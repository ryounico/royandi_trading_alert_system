# Royandi Trading Alert System (RTAS)

Telegram alert-only scanner for Binance USD-M USDT perpetual contracts.
It does **not** place orders and does not need a Binance API key.

## Important strategy assumptions

The supplied research describes:
- 4h Tren long-only
- breakout of a 20-candle high in an uptrend
- exit on a 10-candle low
- ADX minimum 20
- initial stop 4x ATR, capped at 20% from entry
- TP1/TP2 are informational only; user-selected trailing/exit logic remains primary

The research excerpt does not specify the exact trend formula or ATR/ADX periods.
This starter implementation therefore uses provisional, configurable conventions:
- trend proxy: completed 4h close above EMA(50)
- ATR(14), ADX(14)
- TP1 = 2R and TP2 = 3R as reference levels
- breakout is confirmed by a completed 4h close above the prior 20 completed candle highs

These assumptions must be compared with the original backtest implementation before treating signals as strategy-identical.

## Risk sizing

- Per-plan risk is capped at 5 USDT.
- Notional is also capped by 100 USDT capital x 3x leverage.
- This scan limits the sum of its proposed plans to 15 USDT.
- It cannot know manual/open Binance positions because it uses public market data only.
  Therefore it cannot guarantee total account open risk <= 15 USDT.
- No exchange order endpoints or trading keys are used.

## 1. Create a Telegram bot

1. Open Telegram and message `@BotFather`.
2. Send `/newbot`, follow the prompts, and copy the bot token.
3. Open your new bot and send `/start`.
4. In a browser, visit:
   `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
5. Find `message.chat.id` in the response. Keep the token private.
6. Copy `.env.example` to `.env`, then set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

Do not paste the bot token into ChatGPT or public repositories. If exposed, revoke it with BotFather.

## 2. Run locally (Windows)

Install Python 3.12+.

```powershell
py -3.12 -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python main.py
```

The bot sends a startup message. Use `/scan`, `/status`, `/help` in Telegram.

## 3. Run with Docker / VPS

Install Docker and Docker Compose on the VPS, upload this folder, create `.env`, then:

```bash
docker compose up -d --build
docker compose logs -f
```

The container restarts automatically after a VPS reboot.

## 4. Schedule

The scanner aligns to Binance UTC 4h candle closes: 00:00, 04:00, 08:00,
12:00, 16:00, 20:00 UTC (03:00, 07:00, 11:00, 15:00, 19:00, 23:00 WIB).
It waits 20 seconds after the close before requesting data.

## 5. Telegram commands

- `/start` - connection confirmation
- `/scan` - run a manual scan
- `/status` - configuration and last scan
- `/help` - command list

## 6. Suggested VPS sizing

For a personal alert-only scanner, start with 1 vCPU, 1 GB RAM, and a stable
network connection. Upgrade only if the universe or workload requires it.
Public market data is fetched from Binance Futures REST endpoints.

## 7. Before paper-trading

- Compare the provisional EMA/ATR/ADX conventions with the original backtest code.
- Check actual open positions separately; scanner does not read account positions.
- Run at least 30 paper signals and record outcomes.
- Do not use a Binance trading-enabled API key in this alert-only project.
