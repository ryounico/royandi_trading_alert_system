import math
import numpy as np
from .indicators import atr, adx, ema

def analyze(symbol, ticker, klines, book, cfg):
    # Binance kline array: open time, OHLC, base volume, close time, quote volume, ...
    # Exclude the currently-forming candle; use completed 4h bars only.
    now_ms = __import__("time").time() * 1000
    closed = [k for k in klines if int(k[6]) < now_ms]
    if len(closed) < max(cfg.entry_lookback + 5, cfg.ema_period + 5, cfg.adx_period * 3):
        return {"symbol": symbol, "status": "VETO", "reason": "insufficient closed candles"}

    o = np.array([float(k[1]) for k in closed])
    h = np.array([float(k[2]) for k in closed])
    l = np.array([float(k[3]) for k in closed])
    c = np.array([float(k[4]) for k in closed])
    qv = float(ticker.get("quoteVolume", 0))
    last = float(ticker.get("lastPrice", c[-1]))
    atrs = atr(h, l, c, cfg.atr_period)
    adxs = adx(h, l, c, cfg.adx_period)
    emas = ema(c, cfg.ema_period)

    a = float(atrs[-1])
    dx = float(adxs[-1])
    e = float(emas[-1])
    if not all(map(math.isfinite, [a, dx, e])) or a <= 0:
        return {"symbol": symbol, "status": "VETO", "reason": "indicator data unavailable"}

    bid, ask = float(book["bidPrice"]), float(book["askPrice"])
    mid = (bid + ask) / 2
    spread_pct = ((ask - bid) / mid * 100) if mid else 999
    prior_high = float(np.max(h[-cfg.entry_lookback-1:-1]))
    prior_exit_low = float(np.min(l[-cfg.exit_lookback-1:-1]))
    close = float(c[-1])

    # Provisional trend proxy: completed close above EMA(50).
    # The uploaded research defines "uptrend" but does not specify its exact formula.
    trend_ok = close > e
    adx_ok = dx >= cfg.adx_min
    breakout = close > prior_high
    stop_distance = min(cfg.atr_multiple * a, close * cfg.max_stop_pct / 100)
    sl = close - stop_distance
    risk_budget = cfg.risk_per_trade
    raw_qty = risk_budget / stop_distance
    max_notional_qty = (cfg.capital * cfg.leverage) / close
    qty = min(raw_qty, max_notional_qty)
    notional = qty * close
    margin = notional / cfg.leverage
    risk = qty * stop_distance
    tp1, tp2 = close + 2 * stop_distance, close + 3 * stop_distance

    warnings = []
    if spread_pct > cfg.max_spread_pct:
        warnings.append(f"spread {spread_pct:.3f}% > {cfg.max_spread_pct:.3f}%")
    if a / close * 100 > 8:
        warnings.append(f"wide ATR: {a/close*100:.1f}% of price")
    if last - close > cfg.late_entry_atr * a:
        warnings.append(f"late entry: {((last-close)/a):.2f} ATR above rule fill")

    if qv < cfg.min_quote_volume:
        status, reason = "VETO", "24h quote volume below liquidity filter"
    elif spread_pct > cfg.max_spread_pct:
        status, reason = "VETO", "spread exceeds liquidity filter"
    elif not adx_ok:
        status, reason = "VETO", f"ADX {dx:.1f} < {cfg.adx_min:g}"
    elif not trend_ok:
        status, reason = "WAIT", "trend proxy not confirmed (close <= EMA)"
    elif not breakout:
        status, reason = "WAIT", "4h close has not broken prior 20-candle high"
    elif warnings and any(x.startswith("late entry") for x in warnings):
        status, reason = "REVIEW", "breakout confirmed but current price is extended"
    else:
        status, reason = "GO", "completed 4h breakout confirmed"

    return {
        "symbol": symbol, "status": status, "reason": reason, "entry": close,
        "now": last, "sl": sl, "tp1": tp1, "tp2": tp2, "qty": qty,
        "notional": notional, "margin": margin, "risk": risk,
        "atr": a, "adx": dx, "ema": e, "spread_pct": spread_pct,
        "quote_volume": qv, "exit_channel": prior_exit_low, "warnings": warnings,
        "bar_close_ms": int(closed[-1][6])
    }
