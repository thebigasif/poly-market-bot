from polymarket_bot.dependencies import DependencyDetector
from polymarket_bot.models import Market, Condition


def test_detect_same_market_dependencies():
    m = Market(id="m1", question="2024 Election", conditions=[
        Condition(id="c1", market_id="m1", description="Trump wins Pennsylvania", outcome=True),
        Condition(id="c2", market_id="m1", description="Trump wins Ohio", outcome=True),
        Condition(id="c3", market_id="m1", description="Trump wins Wisconsin", outcome=True),
    ])
    det = DependencyDetector()
    deps = det.detect(m)
    assert isinstance(deps, list)
    assert len(deps) > 0


def test_detect_independent_markets():
    m = Market(id="m1", question="Sports", conditions=[
        Condition(id="c1", market_id="m1", description="Lakers win", outcome=True),
        Condition(id="c2", market_id="m1", description="Chess world champion", outcome=True),
    ])
    det = DependencyDetector()
    deps = det.detect(m)
    assert isinstance(deps, list)
    assert len(deps) == 0


def test_llm_dependency_detection_interface():
    class FakeLLM:
        def complete(self, prompt: str) -> str:
            return "YES"

    m = Market(id="m1", question="Election", conditions=[
        Condition(id="c1", market_id="m1", description="Trump wins PA", outcome=True),
        Condition(id="c2", market_id="m1", description="Trump wins OH", outcome=True),
    ])
    det = DependencyDetector(use_llm=True, llm_client=FakeLLM())
    deps = det.detect(m)
    assert len(deps) == 1
    assert deps[0][2] == "llm"
