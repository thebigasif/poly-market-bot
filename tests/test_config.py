from polymarket_bot.config import Settings


def test_defaults():
    s = Settings()
    assert s.dry_run is True
    assert s.min_profit_usd == 0.05
    assert s.max_position_pct == 0.5
    assert s.lookback_minutes == 60
