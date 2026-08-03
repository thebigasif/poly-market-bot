from unittest.mock import MagicMock, patch
from polymarket_bot.clob_client import PolymarketClient
from polymarket_bot.config import Settings


def test_get_markets_returns_list():
    settings = Settings()
    client = PolymarketClient(settings)
    assert hasattr(client, "get_markets")
    assert hasattr(client, "get_orderbook")
    assert hasattr(client, "get_price")
