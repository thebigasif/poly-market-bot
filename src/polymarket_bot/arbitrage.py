import numpy as np
import cvxpy as cp
import math
from typing import List, Dict, Any
from polymarket_bot.models import OrderBook, OrderBookLevel, TradeSignal


class BregmanProjector:
    """Bregman projection with KL divergence onto simplex."""

    def project(self, theta: np.ndarray) -> np.ndarray:
        theta = np.clip(theta, 1e-9, 1.0)
        mu = cp.Variable(len(theta))
        objective = cp.Minimize(-cp.sum(cp.entr(mu)) + mu @ np.log(theta))
        constraints = [mu >= 1e-9, cp.sum(mu) == 1.0]
        prob = cp.Problem(objective, constraints)
        prob.solve(solver=cp.CLARABEL, verbose=False)
        return np.maximum(np.asarray(mu.value, dtype=float), 1e-9)


class IntegerProgrammingOracle:
    """IP oracle for Frank-Wolfe Step 2b: min c^T z over integer constraints."""

    def solve(self, c: np.ndarray, A: np.ndarray, b: np.ndarray, mu: np.ndarray) -> np.ndarray:
        import pulp
        n = len(c)
        c_list = [float(x) for x in np.nan_to_num(c, nan=0.0, posinf=0.0, neginf=0.0)]
        prob = pulp.LpProblem("fw_oracle", pulp.LpMinimize)
        z = [pulp.LpVariable(f"z_{i}", lowBound=0, upBound=1, cat="Binary") for i in range(n)]
        prob += pulp.lpSum(c_list[i] * z[i] for i in range(n))
        for row_idx in range(A.shape[0]):
            prob += pulp.lpSum(A[row_idx, i] * z[i] for i in range(n)) >= b[row_idx]
        prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=30))
        solved_values = []
        for v in z:
            val = pulp.value(v)
            solved_values.append(float(val) if val is not None else 0.0)
        return np.array(solved_values, dtype=float)


class BarrierFrankWolfeArbitrage:
    """Barrier Frank-Wolfe with contracted polytope M' = (1-ε)M + εu."""

    def __init__(self, max_iter: int = 150, eps: float = 1e-6, initial_epsilon: float = 0.1):
        self.max_iter = max_iter
        self.eps = eps
        self.initial_epsilon = initial_epsilon
        self.oracle = IntegerProgrammingOracle()

    def optimal_trade(self, prices: np.ndarray, A: np.ndarray, b: np.ndarray) -> np.ndarray:
        theta = np.clip(prices, 1e-9, 1.0)
        mu = theta.copy()
        epsilon = self.initial_epsilon
        n = len(mu)
        u = np.ones(n) / n
        for iteration in range(self.max_iter):
            theta_bar = (1.0 - epsilon) * theta + epsilon * u
            log_mu = np.where(mu > 1e-12, np.log(mu), np.log(1e-12))
            log_theta_bar = np.where(theta_bar > 1e-12, np.log(theta_bar), np.log(1e-12))
            grad = log_mu - log_theta_bar + 1.0
            grad = np.nan_to_num(grad, nan=0.0, posinf=0.0, neginf=0.0)
            s = self.oracle.solve(grad, A, b, mu)
            s = np.clip(s, -mu + 1e-9, 1.0 - mu + 1e-9)
            gamma = 2.0 / (iteration + 2.0)
            mu_new = np.clip(mu + gamma * (s - mu), 1e-9, 1.0)
            g = float(np.dot(grad, s - mu))
            g_u = float(np.dot(grad, u - mu))
            if g_u < 0:
                g_u = -1e-9
            if g / (-4.0 * g_u) < epsilon:
                epsilon = max(epsilon * 0.95, 1e-9)
            if np.linalg.norm(mu_new - mu) < self.eps:
                break
            mu = mu_new
        return np.clip(mu - theta, -1.0, 1.0)


class Layer1LCMM:
    """Layer 1: simple LCMM constraints, runs in milliseconds."""

    def __init__(self, min_profit: float = 0.05):
        self.min_profit = min_profit

    def scan(self, orderbooks: List[Dict[str, Any]]) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        for ob in orderbooks:
            best_ask = ob.get("best_ask", 1.0)
            best_bid = ob.get("best_bid", 0.0)
            if best_ask + self.min_profit <= best_bid:
                profit = best_bid - best_ask
                signals.append(TradeSignal(
                    condition_id=ob["condition_id"],
                    action="BUY_NO, SELL_YES",
                    size=0.0,
                    expected_profit=profit,
                    confidence=0.9,
                    reason=f"Layer1 LCMM: ask={best_ask:.4f} bid={best_bid:.4f} profit={profit:.4f}",
                ))
        return signals


class Layer2IPProjection:
    """Layer 2: Frank-Wolfe with IP oracle for Bregman projection."""

    def __init__(self, min_profit: float = 0.05):
        self.min_profit = min_profit
        self.fw = BarrierFrankWolfeArbitrage()

    def scan(self, prices: np.ndarray, A: np.ndarray, b: np.ndarray, condition_ids: List[str]) -> List[TradeSignal]:
        delta = self.fw.optimal_trade(prices, A, b)
        profit = float(np.maximum(delta, 0).sum() - np.maximum(-delta, 0).sum())
        if profit < self.min_profit:
            return []
        sigs: List[TradeSignal] = []
        for i, cid in enumerate(condition_ids):
            if abs(delta[i]) > 1e-6:
                action = "BUY_YES" if delta[i] > 0 else "SELL_YES"
                sigs.append(TradeSignal(
                    condition_id=cid,
                    action=action,
                    size=float(abs(delta[i])),
                    expected_profit=profit,
                    confidence=0.7,
                    reason="Layer2 Bregman/Frank-Wolfe IP projection",
                ))
        return sigs


class Layer3ExecutionValidation:
    """Layer 3: simulate fills, check liquidity, slippage, minimum profit."""

    def __init__(self, min_profit: float = 0.05):
        self.min_profit = min_profit

    def validate(self, signal: Dict[str, Any], orderbook: Dict[str, Any]) -> Dict[str, Any]:
        asks = orderbook.get("asks", [])
        bids = orderbook.get("bids", [])
        size = float(signal.get("size", 0.0))
        side = signal.get("direction", "BUY")
        levels = asks if side == "BUY" else bids
        remaining = size
        cost = 0.0
        for lvl in levels:
            take = min(remaining, lvl["size"])
            cost += take * lvl["price"]
            remaining -= take
            if remaining <= 0:
                break
        if remaining > 0:
            cost += remaining * (levels[-1]["price"] if levels else 0.5)
        vwap = cost / size if size > 0 else 0.0
        profit = signal.get("expected_profit", 0.0)
        approved = profit >= self.min_profit and remaining <= 0
        return {
            "approved": approved,
            "vwap": vwap,
            "remaining": remaining,
            "profit": profit,
            "reason": "Layer3 execution validation",
        }


class ArbitrageDetector:
    """Top-level detector matching the article's three-layer architecture."""

    def __init__(self, min_profit: float = 0.05):
        self.layer1 = Layer1LCMM(min_profit=min_profit)
        self.layer2 = Layer2IPProjection(min_profit=min_profit)
        self.layer3 = Layer3ExecutionValidation(min_profit=min_profit)
        self.projector = BregmanProjector()
        self.fw = BarrierFrankWolfeArbitrage()

    def scan_single(self, orderbooks: List[OrderBook]) -> List[TradeSignal]:
        dicts = []
        for ob in orderbooks:
            dicts.append({
                "condition_id": ob.condition_id,
                "best_ask": ob.best_ask,
                "best_bid": ob.best_bid,
                "asks": [{"price": a.price, "size": a.size} for a in ob.asks],
                "bids": [{"price": b.price, "size": b.size} for b in ob.bids],
            })
        return self.layer1.scan(dicts)

    def scan_multi(self, prices: np.ndarray, A: np.ndarray, b: np.ndarray, condition_ids: List[str]) -> List[TradeSignal]:
        return self.layer2.scan(prices, A, b, condition_ids)

    def validate_execution(self, signal: TradeSignal, orderbook: OrderBook) -> Dict[str, Any]:
        ob_dict = {
            "condition_id": orderbook.condition_id,
            "asks": [{"price": a.price, "size": a.size} for a in orderbook.asks],
            "bids": [{"price": b.price, "size": b.size} for b in orderbook.bids],
        }
        sig_dict = {
            "condition_id": signal.condition_id,
            "size": signal.size,
            "direction": "BUY" if "BUY" in signal.action else "SELL",
            "expected_profit": signal.expected_profit,
        }
        return self.layer3.validate(sig_dict, ob_dict)
