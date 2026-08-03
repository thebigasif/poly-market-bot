from typing import List, Optional
from polymarket_bot.clob_client import PolymarketClient
from polymarket_bot.models import Market, Condition, OrderBook


class MarketRepository:
    def __init__(self, client: PolymarketClient):
        self.client = client

    def fetch_active(self, limit: int = 100) -> List[Market]:
        raw = self.client.get_markets(active=True, limit=limit)
        markets: List[Market] = []
        for m in raw:
            conds = [
                Condition(
                    id=tok.get("token_id", ""),
                    market_id=m.get("condition_id", m.get("id", "")),
                    description=tok.get("outcome", ""),
                    outcome=True,
                )
                for tok in m.get("tokens", [])
            ]
            markets.append(Market(
                id=m.get("condition_id", m.get("id", "")),
                question=m.get("question", ""),
                conditions=conds,
                active=m.get("active", True),
                closed=m.get("closed", False),
            ))
        return markets

    def fetch_orderbooks(self, market: Market) -> List[OrderBook]:
        books: List[OrderBook] = []
        for c in market.conditions:
            try:
                books.append(self.client.get_orderbook(c.id))
            except Exception:
                continue
        return books
