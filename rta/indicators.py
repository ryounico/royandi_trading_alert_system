import numpy as np

def ema(values, period):
    values = np.asarray(values, dtype=float)
    if len(values) < period:
        return np.full(len(values), np.nan)
    out = np.full(len(values), np.nan)
    out[period - 1] = values[:period].mean()
    alpha = 2.0 / (period + 1.0)
    for i in range(period, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out

def wilder(values, period):
    values = np.asarray(values, dtype=float)
    out = np.full(len(values), np.nan)
    if len(values) <= period:
        return out
    out[period] = np.nanmean(values[1:period + 1])
    for i in range(period + 1, len(values)):
        out[i] = (out[i - 1] * (period - 1) + values[i]) / period
    return out

def atr(high, low, close, period=14):
    high, low, close = map(lambda x: np.asarray(x, dtype=float), (high, low, close))
    prev = np.roll(close, 1)
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev), np.abs(low - prev)))
    tr[0] = high[0] - low[0]
    return wilder(tr, period)

def adx(high, low, close, period=14):
    high, low, close = map(lambda x: np.asarray(x, dtype=float), (high, low, close))
    up = np.diff(high, prepend=high[0])
    down = -np.diff(low, prepend=low[0])
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    a = atr(high, low, close, period)
    pdi = 100 * wilder(plus_dm, period) / np.where(a == 0, np.nan, a)
    mdi = 100 * wilder(minus_dm, period) / np.where(a == 0, np.nan, a)
    dx = 100 * np.abs(pdi - mdi) / np.where((pdi + mdi) == 0, np.nan, pdi + mdi)
    return wilder(dx, period)
