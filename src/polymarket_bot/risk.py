import math
from polymarket_bot.config import Settings
from polymarket_bot.models import TradeSignal


class RiskManager:
    def __init__(self, settings: Settings):
        self.min_profit = settings.min_profit_usd
        self.max_position_pct = settings.max_position_pct

    def size_position(self, signal: TradeSignal, bankroll: float, p_exec: float) -> float:
        """
        Modified Kelly criterion accounting for execution risk.
        Formula from article: f = (b×p - q) / b × sqrt(p)
        """
        b = signal.expected_profit
        p = max(min(p_exec, 0.99), 0.01)
        q = 1.0 - p
        if b <= 0:
            return 0.0
        kelly = (b * p - q) / b
        kelly = kelly * math.sqrt(p)
        cap = bankroll * self.max_position_pct
        return max(0.0, min(kelly * bankroll, cap))
