import numpy as np
from polymarket_bot.arbitrage import (
    BregmanProjector,
    BarrierFrankWolfeArbitrage,
    Layer1LCMM,
    Layer2IPProjection,
    Layer3ExecutionValidation,
    ArbitrageDetector,
)
from polymarket_bot.models import OrderBook, OrderBookLevel, TradeSignal


def test_bregman_projection_simplex():
    theta = np.array([0.6, 0.4])
    proj = BregmanProjector()
    mu = proj.project(theta)
    assert abs(mu.sum() - 1.0) < 1e-3
    assert np.all(mu > 0)


def test_bregman_projection_out_of_simplex():
    theta = np.array([0.9, 1.2, 0.3])
    proj = BregmanProjector()
    mu = proj.project(theta)
    assert abs(mu.sum() - 1.0) < 1e-3
    assert np.all(mu > 0)


def test_fw_with_ip_oracle_simple():
    prices = np.array([0.6, 0.4])
    A = np.array([[1.0, 1.0]])
    b = np.array([1.0])
    fw = BarrierFrankWolfeArbitrage(max_iter=150, eps=1e-6, initial_epsilon=0.1)
    delta = fw.optimal_trade(prices, A, b)
    assert delta.shape == (2,)


def test_layer1_detects_single_condition():
    books = [
        {
            "condition_id": "c1",
            "best_ask": 0.30,
            "best_bid": 0.60,
            "asks": [{"price": 0.30, "size": 100.0}],
            "bids": [{"price": 0.60, "size": 100.0}],
        },
    ]
    layer = Layer1LCMM(min_profit=0.05)
    sigs = layer.scan(books)
    assert len(sigs) > 0


def test_layer1_no_arb_when_efficient():
    books = [
        {
            "condition_id": "c1",
            "best_ask": 0.50,
            "best_bid": 0.50,
            "asks": [{"price": 0.50, "size": 100.0}],
            "bids": [{"price": 0.50, "size": 100.0}],
        },
    ]
    layer = Layer1LCMM(min_profit=0.05)
    sigs = layer.scan(books)
    assert len(sigs) == 0


def test_layer2_multi_condition():
    prices = np.array([0.3, 0.4, 0.2])
    A = np.ones((1, 3))
    b = np.array([1.0])
    cids = ["c1", "c2", "c3"]
    layer = Layer2IPProjection(min_profit=0.05)
    sigs = layer.scan(prices, A, b, cids)
    assert isinstance(sigs, list)


def test_layer3_execution_validation():
    sig = {"condition_id": "c1", "size": 10.0, "direction": "BUY", "expected_profit": 0.2}
    book = {
        "condition_id": "c1",
        "asks": [{"price": 0.30, "size": 100.0}],
        "bids": [{"price": 0.60, "size": 100.0}],
    }
    layer = Layer3ExecutionValidation(min_profit=0.05)
    result = layer.validate(sig, book)
    assert result["approved"] is True
    assert result["remaining"] == 0.0


def test_layer3_blocks_insufficient_liquidity():
    sig = {"condition_id": "c1", "size": 200.0, "direction": "BUY", "expected_profit": 0.2}
    book = {
        "condition_id": "c1",
        "asks": [{"price": 0.30, "size": 100.0}],
        "bids": [{"price": 0.60, "size": 100.0}],
    }
    layer = Layer3ExecutionValidation(min_profit=0.05)
    result = layer.validate(sig, book)
    assert result["approved"] is False
    assert result["remaining"] > 0


def test_full_detector_single_condition():
    ob = OrderBook(
        condition_id="c1",
        bids=[OrderBookLevel(price=0.60, size=100.0)],
        asks=[OrderBookLevel(price=0.30, size=100.0)],
    )
    det = ArbitrageDetector(min_profit=0.05)
    sigs = det.scan_single([ob])
    assert len(sigs) > 0


def test_full_detector_no_arb():
    ob = OrderBook(
        condition_id="c1",
        bids=[OrderBookLevel(price=0.50, size=100.0)],
        asks=[OrderBookLevel(price=0.50, size=100.0)],
    )
    det = ArbitrageDetector(min_profit=0.05)
    sigs = det.scan_single([ob])
    assert len(sigs) == 0


def test_validate_execution_integration():
    ob = OrderBook(
        condition_id="c1",
        bids=[OrderBookLevel(price=0.60, size=100.0)],
        asks=[OrderBookLevel(price=0.30, size=100.0)],
    )
    sig = TradeSignal(
        condition_id="c1",
        action="BUY_NO",
        size=10.0,
        expected_profit=0.3,
        confidence=0.8,
        reason="test",
    )
    det = ArbitrageDetector(min_profit=0.05)
    result = det.validate_execution(sig, ob)
    assert result["approved"] is True
