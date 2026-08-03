import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    polymarket_api_url: str = os.getenv("POLYMARKET_API_URL", "https://clob.polymarket.com")
    polymarket_ws_url: str = os.getenv("POLYMARKET_WS_URL", "wss://ws-subscriptions-clob.polymarket.com/ws/market")
    polymarket_api_key: str = os.getenv("POLYMARKET_API_KEY", "")
    polymarket_api_secret: str = os.getenv("POLYMARKET_API_SECRET", "")
    polymarket_api_passphrase: str = os.getenv("POLYMARKET_API_PASSPHRASE", "")
    dry_run: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    min_profit_usd: float = float(os.getenv("MIN_PROFIT_USD", "0.05"))
    max_position_pct: float = float(os.getenv("MAX_POSITION_PCT", "0.5"))
    lookback_minutes: int = int(os.getenv("LOOKBACK_MINUTES", "60"))
