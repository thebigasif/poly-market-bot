import streamlit as st
from polymarket_bot.config import Settings
from polymarket_bot.clob_client import PolymarketClient
from polymarket_bot.markets import MarketRepository
from polymarket_bot.arbitrage import ArbitrageDetector
from polymarket_bot.execution import ExecutionEngine

st.set_page_config(page_title="Polymarket Arbitrage Bot", layout="wide")
st.title("Polymarket Arbitrage Bot")

settings = Settings()
client = PolymarketClient(settings)
repo = MarketRepository(client)
det = ArbitrageDetector(min_profit=settings.min_profit_usd)
eng = ExecutionEngine(settings)

col1, col2, col3 = st.columns(3)
col1.metric("Mode", "DRY RUN" if settings.dry_run else "LIVE")
col2.metric("Min Profit", f"${settings.min_profit_usd:.2f}")
col3.metric("Max Position", f"{settings.max_position_pct*100:.0f}%")

st.subheader("Markets")
markets = repo.fetch_active(limit=50)
for market in markets[:20]:
    with st.expander(market.question):
        books = repo.fetch_orderbooks(market)
        signals = det.scan_single(books)
        if signals:
            st.error(f"{len(signals)} arbitrage signal(s)")
            for sig in signals:
                st.write(f"- {sig.reason}: profit={sig.expected_profit:.4f}")
                if st.button(f"Execute {sig.condition_id}", key=f"exec_{sig.condition_id}"):
                    eng.execute(sig)
                    st.success("Submitted (dry-run)")
        else:
            st.write("No arbitrage detected")
