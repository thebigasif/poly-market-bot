from typing import List, Tuple, Dict, Any, Optional, Protocol
from polymarket_bot.models import Market, Condition


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        ...


class DependencyDetector:
    """Detect logical dependencies between conditions/markets."""

    def __init__(self, use_llm: bool = False, llm_client: Optional[LLMClient] = None):
        self.use_llm = use_llm
        self.llm_client = llm_client

    def detect(self, market: Market) -> List[Tuple[str, str, str]]:
        deps: List[Tuple[str, str, str]] = []
        if self.use_llm and self.llm_client is not None:
            return self._detect_with_llm(market)
        return self._detect_heuristic(market)

    def _detect_heuristic(self, market: Market) -> List[Tuple[str, str, str]]:
        deps: List[Tuple[str, str, str]] = []
        conds = market.conditions
        n = len(conds)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = conds[i], conds[j]
                score = self._similarity(a.description, b.description)
                if score > 0.35:
                    deps.append((a.id, b.id, "heuristic"))
        return deps

    def _detect_with_llm(self, market: Market) -> List[Tuple[str, str, str]]:
        deps: List[Tuple[str, str, str]] = []
        conds = market.conditions
        n = len(conds)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = conds[i], conds[j]
                prompt = (
                    "Are these two prediction-market conditions logically dependent?\n"
                    f"A: {a.description}\nB: {b.description}\n"
                    "Answer YES or NO only."
                )
                try:
                    answer = self.llm_client.complete(prompt).strip().upper()
                except Exception:
                    answer = "NO"
                if answer.startswith("Y"):
                    deps.append((a.id, b.id, "llm"))
        return deps

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        tokens_a = set(a.lower().split())
        tokens_b = set(b.lower().split())
        if not tokens_a or not tokens_b:
            return 0.0
        return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
