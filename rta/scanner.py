import asyncio
import aiohttp
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .binance import BinancePublic
from .strategy import analyze

def fmt(x):
    if x is None: return "—"
    return f"{x:.8g}"

class Scanner:
    def __init__(self, cfg):
        self.cfg = cfg
        self.api = BinancePublic(cfg.binance_base, cfg.concurrency)

    async def scan(self):
        # Reuse one HTTPS session for the entire scan. This avoids opening
        # hundreds of short-lived TLS connections during a full-universe scan.
        connector = aiohttp.TCPConnector(limit=self.cfg.concurrency, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=60, connect=15, sock_read=40)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            universe, listed_count, missing_tickers = await self.api.universe(session)
            # Analyze every listed USDT perpetual returned by exchangeInfo.
            # Liquidity is a status/warning in strategy.py, not a universe exclusion.
            eligible = list(universe.items())
            eligible.sort(key=lambda x: float(x[1].get("quoteVolume", 0)), reverse=True)
            if self.cfg.max_symbols:
                eligible = eligible[:self.cfg.max_symbols]

            sem = asyncio.Semaphore(self.cfg.concurrency)
            async def one(symbol, ticker):
                async with sem:
                    try:
                        kl, book = await asyncio.gather(
                            self.api.klines(session, symbol),
                            self.api.book_ticker(session, symbol),
                        )
                        return analyze(symbol, ticker, kl, book, self.cfg)
                    except Exception as e:
                        return {"symbol": symbol, "status": "ERROR",
                                "reason": f"{type(e).__name__}: {e}"}

            results = await asyncio.gather(*(one(s, t) for s, t in eligible))

        results.sort(key=lambda x: ({"GO":0, "REVIEW":1, "WAIT":2, "VETO":3, "ERROR":4}.get(x["status"], 5),
                                    -x.get("quote_volume", 0)))
        # Attach universe accounting so reports distinguish filtered, scanned,
        # and missing ticker symbols.
        self.last_universe_stats = {
            "listed_usdt_perpetual": listed_count,
            "ticker_received": len(universe),
            "missing_ticker": missing_tickers,
            "liquidity_eligible": len(eligible),
            "analyzed": len(results),
        }
        return results

def render_report(results, cfg, stats=None):
    now = datetime.now(ZoneInfo(cfg.timezone)).strftime("%Y-%m-%d %H:%M %Z")
    plans = [x for x in results if x["status"] in ("GO", "REVIEW")]
    # This cap applies only to this scan's proposed plans, not real exchange positions.
    chosen, total_risk = [], 0.0
    for p in plans:
        if len(chosen) >= 3 or total_risk + p["risk"] > cfg.max_total_risk:
            continue
        chosen.append(p)
        total_risk += p["risk"]

    stats = stats or {}
    lines = [f"📡 <b>ROYANDI TRADING ALERT</b>", f"Scan: {now} · Binance USD-M · 4H",
             f"Listed USDT perpetual: {stats.get('listed_usdt_perpetual', 'N/A')} · Ticker received: {stats.get('ticker_received', 'N/A')}",
             f"Analyzed: {stats.get('analyzed', len(results))} · Missing ticker: {stats.get('missing_ticker', 'N/A')}"]
    for p in chosen:
        lines += ["", f"<b>LONG {p['symbol']} · {p['status']}</b>",
                  f"Buy ~{fmt(p['entry'])} (now {fmt(p['now'])})",
                  f"SL {fmt(p['sl'])} · TP1 {fmt(p['tp1'])} · TP2 {fmt(p['tp2'])}",
                  f"Qty {fmt(p['qty'])} · Notional {p['notional']:.2f} USDT · Margin {p['margin']:.2f} USDT · Risk {p['risk']:.2f} USDT",
                  f"ADX {p['adx']:.1f} · ATR {p['atr']:.8g}"]
        for w in p.get("warnings", []):
            lines.append(f"⚠️ {w}")
    if not chosen:
        lines += ["", "Tidak ada setup GO/REVIEW yang lolos filter pada scan ini."]
    counts = {s: sum(1 for x in results if x["status"] == s) for s in ("GO","REVIEW","WAIT","VETO","ERROR")}
    lines += ["", f"<b>Summary</b>: GO {counts['GO']} · REVIEW {counts['REVIEW']} · WAIT {counts['WAIT']} · VETO {counts['VETO']} · ERROR {counts['ERROR']}",
              f"Proposed risk: {total_risk:.2f}/{cfg.max_total_risk:.2f} USDT",
              "Catatan: risiko ini hanya rencana dari scanner; posisi akun Binance aktual belum dibaca.",
              "TP1/TP2 hanya referensi (2R/3R). Rule exit: trailing 2R + exit 10-candle low; bot ini belum memantau posisi berjalan.",
              "Analisis saja — tidak ada order yang dikirim."]
    if cfg.report_all:
        others = [x for x in results if x["status"] in ("WAIT","VETO","ERROR")]
        lines += ["", "<b>Watchlist (ringkas)</b>"]
        for x in others[:25]:
            lines.append(f"• {x['symbol']}: {x['status']} — {x['reason']}")
        if len(others) > 25:
            lines.append(f"… dan {len(others)-25} pair lainnya.")
    return "\n".join(lines)
