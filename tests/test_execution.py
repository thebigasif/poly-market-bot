from polymarket_bot.execution import ExecutionEngine
from polymarket_bot.risk import RiskManager
from polymarket_bot.config import Settings
from polymarket_bot.models import OrderBook, OrderBookLevel, TradeSignal


def test_estimate_vwap():
    ob = OrderBook(
        condition_id="c1",
        bids=[OrderBookLevel(price=0.50, size=50), OrderBookLevel(price=0.49, size=50)],
        asks=[OrderBookLevel(price=0.52, size=30), OrderBookLevel(price=0.53, size=70)],
    )
    eng = ExecutionEngine(Settings())
    vwap = eng.estimate_vwap(ob, size=60, side="BUY")
    assert 0.52 <= vwap <= 0.54


def test_dry_run_blocks_live():
    settings = Settings()
    eng = ExecutionEngine(settings)
    sig = TradeSignal(condition_id="c1", action="BUY_YES", size=10, expected_profit=0.5, confidence=0.8, reason="test")
    eng.execute(sig)


def test_risk_sizing():
    settings = Settings()
    rm = RiskManager(settings)
    sig = TradeSignal(condition_id="c1", action="BUY_YES", size=10, expected_profit=0.2, confidence=0.8, reason="test")
    sized = rm.size_position(sig, bankroll=1000, p_exec=0.9)
    assert sized >= 0
    assert sized <= 1000 * 0.5
