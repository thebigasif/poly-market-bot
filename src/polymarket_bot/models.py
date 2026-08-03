from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Condition:
    id: str
    market_id: str
    description: str
    outcome: bool
    tag: Optional[str] = None


@dataclass
class Market:
    id: str
    question: str
    conditions: List[Condition]
    active: bool = True
    closed: bool = False


@dataclass
class OrderBookLevel:
    price: float
    size: float


@dataclass
class OrderBook:
    condition_id: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]

    @property
    def best_bid(self) -> float:
        return max((b.price for b in self.bids), default=0.0)

    @property
    def best_ask(self) -> float:
        return min((a.price for a in self.asks), default=1.0)

    @property
    def spread(self) -> float:
        return self.best_ask - self.best_bid


@dataclass
class TradeSignal:
    condition_id: str
    action: str  # BUY_YES, BUY_NO, SELL_YES, SELL_NO
    size: float
    expected_profit: float
    confidence: float
    reason: str
