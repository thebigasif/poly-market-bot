from polymarket_bot.models import Condition, Market, OrderBookLevel, OrderBook, TradeSignal


def test_condition_validation():
    c = Condition(id="c1", market_id="m1", description="Trump wins PA", outcome=True)
    assert c.id == "c1"


def test_orderbook_best_bid_ask():
    ob = OrderBook(
        condition_id="c1",
        bids=[OrderBookLevel(price=0.50, size=100.0)],
        asks=[OrderBookLevel(price=0.55, size=80.0)],
    )
    assert ob.best_bid == 0.50
    assert ob.best_ask == 0.55
    assert abs(ob.spread - 0.05) < 1e-9


def test_trade_signal_defaults():
    sig = TradeSignal(
        condition_id="c1",
        action="BUY_YES",
        size=10.0,
        expected_profit=0.5,
        confidence=0.8,
        reason="test",
    )
    assert sig.action == "BUY_YES"
