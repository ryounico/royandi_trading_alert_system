from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Config:
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    timezone: str = os.getenv("TIMEZONE", "Asia/Jakarta")
    capital: float = float(os.getenv("CAPITAL_USDT", "100"))
    risk_per_trade: float = float(os.getenv("RISK_PER_TRADE_USDT", "5"))
    max_total_risk: float = float(os.getenv("MAX_TOTAL_RISK_USDT", "15"))
    leverage: float = float(os.getenv("LEVERAGE", "3"))
    min_quote_volume: float = float(os.getenv("MIN_QUOTE_VOLUME_USDT", "20000000"))
    max_spread_pct: float = float(os.getenv("MAX_SPREAD_PCT", "0.15"))
    max_symbols: int = int(os.getenv("MAX_SYMBOLS", "0"))  # 0 = all eligible symbols
    concurrency: int = int(os.getenv("CONCURRENCY", "8"))
    adx_min: float = float(os.getenv("ADX_MIN", "20"))
    atr_period: int = int(os.getenv("ATR_PERIOD", "14"))
    adx_period: int = int(os.getenv("ADX_PERIOD", "14"))
    ema_period: int = int(os.getenv("EMA_PERIOD", "50"))
    entry_lookback: int = int(os.getenv("ENTRY_LOOKBACK", "20"))
    exit_lookback: int = int(os.getenv("EXIT_LOOKBACK", "10"))
    atr_multiple: float = float(os.getenv("ATR_MULTIPLE", "4"))
    max_stop_pct: float = float(os.getenv("MAX_STOP_PCT", "20"))
    late_entry_atr: float = float(os.getenv("LATE_ENTRY_ATR", "0.75"))
    report_all: bool = os.getenv("REPORT_ALL", "true").lower() == "true"
    run_scan_on_start: bool = os.getenv("RUN_SCAN_ON_START", "false").lower() == "true"
    binance_base: str = os.getenv("BINANCE_FAPI_BASE", "https://fapi.binance.com")
