# Polymarket Arbitrage Bot

Exact-match implementation of the arbitrage system described in RohOnChain's article: Bregman projection, Barrier Frank-Wolfe with integer-programming oracle, three-layer optimization engine, and modified Kelly position sizing.

## Setup

```bash
cd ~/Desktop/polymarket-bot
source .venv/bin/activate
pip install -e .
```

## Run Dashboard

```bash
source .venv/bin/activate
streamlit run src/polymarket_bot/dashboard.py
```

## Run Bot

```bash
python src/polymarket_bot/main.py
```

## Architecture

### Article mapping

| Article component | Implementation |
|---|---|
| Single-condition LCMM | `Layer1LCMM` — fast linear-programming relaxation |
| Bregman projection | `BregmanProjector` — KL divergence onto simplex |
| Barrier Frank-Wolfe | `BarrierFrankWolfeArbitrage` — contracted polytope `M' = (1-ε)M + εu` |
| IP oracle Step 2b | `IntegerProgrammingOracle` — binary `min c^T z` via PuLP/CBC |
| Multi-condition arbitrage | `Layer2IPProjection` — FW + IP oracle over `A^T z >= b` |
| Execution validation | `Layer3ExecutionValidation` — VWAP, liquidity, slippage, $0.05 threshold |
| Dependency detection | `DependencyDetector` — heuristic + LLM interface (`use_llm=True`) |
| Time-window grouping | `TimeWindowGrouper` — 950-block windows (~1 hour on Polygon) |
| Position sizing | `RiskManager` — modified Kelly: `f = (b×p - q)/b × sqrt(p)` |
| LLM dependency filter | `DependencyDetector(use_llm=True, llm_client=...)` |

### How it matches the article

- **Layer 1**: LCMM constraints run in milliseconds, removing obvious mispricing
- **Layer 2**: Frank-Wolfe with Barrier trick (`ε` adaptive 0.1 → 1e-9), IP oracle via PuLP/CBC with 30s time limit, 150 max iterations
- **Layer 3**: Execution validation with VWAP, liquidity check, minimum $0.05 profit threshold
- **Bregman projection**: KL divergence for LMSR markets: `min -∑entr(μ) + μ·log(θ)` subject to `μ ≥ 0, ∑μ = 1`
- **Adaptive ε**: decreases when `g / (-4·g_u) < ε`, matching article's controlled growth problem
- **Modified Kelly**: `sqrt(p)` adjustment for execution risk, capped at `max_position_pct` of bankroll
- **Dry-run by default**: `DRY_RUN=true` in `.env.example`; live execution requires explicit opt-in + API key

## Safety

- Default: `DRY_RUN=true` — no real trades.
- Enable live only with `DRY_RUN=false` + valid `POLYMARKET_API_KEY`.
- Start small. The article's top arbitrageur ran $500K+ capital with systematic execution.

## Disclaimer

This is educational software. Trading involves risk. You are responsible for your own decisions.
