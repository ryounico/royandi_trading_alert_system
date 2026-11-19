import asyncio
import aiohttp


class BinancePublic:
    """Public USD-M Futures market-data client. No API key is required."""

    def __init__(self, base, concurrency=8):
        self.base = base.rstrip("/")
        self.sem = asyncio.Semaphore(concurrency)
        self.timeout = aiohttp.ClientTimeout(total=45, connect=15, sock_read=30)

    async def get(self, session, path, params=None, attempts=3):
        url = self.base + path
        last_error = None
        for attempt in range(attempts):
            try:
                async with self.sem:
                    async with session.get(url, params=params, timeout=self.timeout) as resp:
                        if resp.status in (418, 429):
                            retry_after = resp.headers.get("Retry-After", "unknown")
                            raise RuntimeError(
                                f"Binance rate limit HTTP {resp.status}; Retry-After={retry_after}"
                            )
                        resp.raise_for_status()
                        return await resp.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    await asyncio.sleep(1.5 * (attempt + 1))
        if isinstance(last_error, asyncio.TimeoutError):
            raise RuntimeError(f"Timeout saat mengakses {path} setelah {attempts} percobaan") from last_error
        if last_error is not None:
            raise RuntimeError(f"Gagal mengakses {path}: {type(last_error).__name__}: {last_error}") from last_error
        raise RuntimeError(f"Gagal mengakses {path}")

    async def universe(self, session):
        # Bulk endpoints: one request each for exchange metadata and 24h ticker.
        info, tickers = await asyncio.gather(
            self.get(session, "/fapi/v1/exchangeInfo"),
            self.get(session, "/fapi/v1/ticker/24hr"),
        )
        tradable = {
            x["symbol"] for x in info.get("symbols", [])
            if x.get("status") == "TRADING"
            and x.get("contractType") == "PERPETUAL"
            and x.get("quoteAsset") == "USDT"
        }
        by_symbol = {x["symbol"]: x for x in tickers if x.get("symbol") in tradable}
        missing = tradable - set(by_symbol)
        return by_symbol, len(tradable), len(missing)

    async def klines(self, session, symbol, limit=120):
        return await self.get(
            session, "/fapi/v1/klines",
            {"symbol": symbol, "interval": "4h", "limit": limit},
        )

    async def book_ticker(self, session, symbol):
        return await self.get(
            session, "/fapi/v1/ticker/bookTicker", {"symbol": symbol}
        )
