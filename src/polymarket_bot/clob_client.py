import requests
import asyncio
import json
from typing import List, Optional, Callable, Any
from polymarket_bot.config import Settings
from polymarket_bot.models import Market, OrderBook, OrderBookLevel


class PolymarketClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base = settings.polymarket_api_url.rstrip("/")
        self.session = requests.Session()

    def get_markets(self, active: bool = True, closed: bool = False, limit: int = 100) -> List[dict]:
        params = {"active": str(active).lower(), "closed": str(closed).lower(), "limit": limit}
        r = self.session.get(f"{self.base}/markets", params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def get_orderbook(self, token_id: str) -> OrderBook:
        r = self.session.get(f"{self.base}/book", params={"token_id": token_id}, timeout=15)
        r.raise_for_status()
        data = r.json()
        bids = [OrderBookLevel(price=float(b["price"]), size=float(b["size"])) for b in data.get("bids", [])]
        asks = [OrderBookLevel(price=float(a["price"]), size=float(a["size"])) for a in data.get("asks", [])]
        return OrderBook(condition_id=token_id, bids=bids, asks=asks)

    def get_price(self, token_id: str, side: str = "BUY") -> float:
        ob = self.get_orderbook(token_id)
        return ob.best_ask if side == "BUY" else ob.best_bid

    async def subscribe_orderbooks(self, token_ids: List[str], callback: Callable[[dict], Any]):
        import websockets
        uri = self.settings.polymarket_ws_url
        async with websockets.connect(uri) as ws:
            sub = {"type": "subscribe", "markets": token_ids}
            await ws.send(json.dumps(sub))
            async for raw in ws:
                msg = json.loads(raw)
                if msg.get("event_type") == "book":
                    callback(msg)
