import logging
import time
from typing import List, Dict, Any, Optional
from polymarket_bot.config import Settings
from polymarket_bot.models import OrderBook, OrderBookLevel, TradeSignal

logger = logging.getLogger(__name__)


class TimeWindowGrouper:
    """Group trades into 950-block windows (~1 hour on Polygon)."""

    def __init__(self, window_blocks: int = 950):
        self.window_blocks = window_blocks
        self.windows: Dict[str, List[Dict[str, Any]]] = {}

    def add(self, trade: Dict[str, Any]):
        trader = trade.get("trader", "unknown")
        block = trade.get("block", 0)
        window_key = f"{trader}:{block // self.window_blocks}"
        self.windows.setdefault(window_key, []).append(trade)

    def get_windows(self) -> List[List[Dict[str, Any]]]:
        return list(self.windows.values())


class ExecutionEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.live = (not settings.dry_run) and bool(settings.polymarket_api_key)
        self.grouper = TimeWindowGrouper()

    def estimate_vwap(self, book: OrderBook, size: float, side: str = "BUY") -> float:
        levels = book.asks if side == "BUY" else book.bids
        remaining = size
        cost = 0.0
        for lvl in levels:
            take = min(remaining, lvl.size)
            cost += take * lvl.price
            remaining -= take
            if remaining <= 0:
                break
        if remaining > 0:
            fallback = 0.5
            cost += remaining * fallback
        return cost / size if size > 0 else 0.0

    def execute(self, signal: TradeSignal):
        if not self.live:
            logger.info("DRY_RUN: %s %s size=%.4f expected_profit=%.4f", signal.action, signal.condition_id, signal.size, signal.expected_profit)
            return
        raise NotImplementedError("Live execution not implemented in v0.1")
