import asyncio
import aiohttp

async def main():
    url = "https://fapi.binance.com/fapi/v1/ping"
    timeout = aiohttp.ClientTimeout(total=20)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                print("HTTP STATUS:", response.status)
                print("RESPONSE:", await response.text())
    except Exception as error:
        print("CONNECTION ERROR:", repr(error))

asyncio.run(main())