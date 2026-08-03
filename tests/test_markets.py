from unittest.mock import patch
from polymarket_bot.markets import MarketRepository
from polymarket_bot.clob_client import PolymarketClient
from polymarket_bot.config import Settings


@patch("polymarket_bot.clob_client.requests.Session.get")
def test_fetch_active_markets(mock_get):
    mock_get.return_value.json.return_value = [
        {
            "condition_id": "m1",
            "question": "Test market",
            "active": True,
            "closed": False,
            "tokens": [
                {"token_id": "c1", "outcome": "Yes"},
                {"token_id": "c2", "outcome": "No"},
            ],
        }
    ]
    settings = Settings()
    client = PolymarketClient(settings)
    repo = MarketRepository(client)
    markets = repo.fetch_active(limit=5)
    assert isinstance(markets, list)
    assert len(markets) == 1
    assert markets[0].id == "m1"
    assert markets[0].question == "Test market"
    assert len(markets[0].conditions) == 2
