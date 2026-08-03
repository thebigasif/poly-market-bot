import asyncio
import logging
import numpy as np
from polymarket_bot.config import Settings
from polymarket_bot.clob_client import PolymarketClient
from polymarket_bot.markets import MarketRepository
from polymarket_bot.dependencies import DependencyDetector
from polymarket_bot.arbitrage import ArbitrageDetector
from polymarket_bot.execution import ExecutionEngine
from polymarket_bot.risk import RiskManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Bot:
    def __init__(self):
        self.settings = Settings()
        self.client = PolymarketClient(self.settings)
        self.repo = MarketRepository(self.client)
        self.detector = DependencyDetector()
        self.arb = ArbitrageDetector(min_profit=self.settings.min_profit_usd)
        self.eng = ExecutionEngine(self.settings)
        self.risk = RiskManager(self.settings)

    def run_once(self):
        markets = self.repo.fetch_active(limit=100)
        for market in markets:
            books = self.repo.fetch_orderbooks(market)
            signals = self.arb.scan_single(books)
            for sig in signals:
                logger.info("SIGNAL: %s", sig.reason)
                self.eng.execute(sig)
            if len(books) >= 2:
                prices = np.array([ob.best_ask for ob in books])
                A = np.ones((1, len(books)))
                b = np.array([1.0])
                cids = [ob.condition_id for ob in books]
                msigs = self.arb.scan_multi(prices, A, b, cids)
                for sig in msigs:
                    logger.info("MULTI SIGNAL: %s", sig.reason)
                    self.eng.execute(sig)

    def loop(self):
        logger.info("Bot started. dry_run=%s", self.settings.dry_run)
        while True:
            try:
                self.run_once()
            except Exception as exc:
                logger.exception("Loop error: %s", exc)
            import time
            time.sleep(self.settings.lookback_minutes * 60)


def main():
    bot = Bot()
    bot.loop()


if __name__ == "__main__":
    main()
