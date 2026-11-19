
import asyncio
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from .config import Config
from .scanner import Scanner, render_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

cfg = Config()
scanner = Scanner(cfg)
last_scan = "Belum ada scan pada sesi ini."


def allowed(update):
    return (
        bool(cfg.telegram_chat_id)
        and str(update.effective_chat.id) == str(cfg.telegram_chat_id)
    )


def get_bot(app_or_bot):
    return app_or_bot.bot if hasattr(app_or_bot, "bot") else app_or_bot


async def send_report(app_or_bot, report):
    bot = get_bot(app_or_bot)

    for i in range(0, len(report), 3900):
        await bot.send_message(
            chat_id=cfg.telegram_chat_id,
            text=report[i:i + 3900],
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )


def is_new_go(symbol, bar_close_ms):
    db = sqlite3.connect("rtas_state.sqlite3")

    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS sent_go (
                symbol TEXT,
                bar_close_ms INTEGER,
                PRIMARY KEY(symbol, bar_close_ms)
            )
        """)

        cur = db.execute(
            """
            INSERT OR IGNORE INTO sent_go(symbol, bar_close_ms)
            VALUES (?, ?)
            """,
            (symbol, bar_close_ms)
        )

        db.commit()
        return cur.rowcount == 1

    finally:
        db.close()


async def run_scan(app_or_bot):
    global last_scan

    results = await scanner.scan()

    report = render_report(
        results,
        cfg,
        getattr(scanner, "last_universe_stats", {})
    )

    last_scan = datetime.now(
        ZoneInfo(cfg.timezone)
    ).strftime("%Y-%m-%d %H:%M %Z")

    await send_report(app_or_bot, report)

    for p in results:
        if (
            p.get("status") == "GO"
            and is_new_go(p["symbol"], p["bar_close_ms"])
        ):
            alert = (
                f"🚀 <b>NEW GO SIGNAL · LONG {p['symbol']}</b>\n"
                f"Buy ~{p['entry']:.8g} · now {p['now']:.8g}\n"
                f"SL {p['sl']:.8g} · TP1 {p['tp1']:.8g} · TP2 {p['tp2']:.8g}\n"
                f"Qty {p['qty']:.8g} · Risk {p['risk']:.2f} USDT\n"
                f"ADX {p['adx']:.1f} · ATR {p['atr']:.8g}\n"
                "Alert only — verifikasi eksposur akun dan kondisi harga sebelum mengambil keputusan."
            )

            await send_report(app_or_bot, alert)

    return report


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        await update.message.reply_text("Chat belum diizinkan.")
        return

    await update.message.reply_text(
        "RTAS aktif. Gunakan /scan, /status, atau /help."
    )


async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    await update.message.reply_text(
        "Scan dimulai. Laporan akan dikirim setelah selesai."
    )

    try:
        await run_scan(context.application)
    except Exception as e:
        logging.exception("Manual scan failed")
        await update.message.reply_text(f"Scan gagal: {e}")


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    await update.message.reply_text(
        f"RTAS aktif\n"
        f"Modal: {cfg.capital:.2f} USDT\n"
        f"Risk/trade: {cfg.risk_per_trade:.2f} USDT\n"
        f"Max total planned risk: {cfg.max_total_risk:.2f} USDT\n"
        f"Leverage sizing: {cfg.leverage:g}x\n"
        f"Time zone: {cfg.timezone}\n"
        f"Last scan: {last_scan}\n"
        "Mode: alert-only, no order execution."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    await update.message.reply_text(
        "/scan - jalankan scan manual\n"
        "/status - konfigurasi dan scan terakhir\n"
        "/help - bantuan"
    )


def seconds_to_next_4h_close():
    now = datetime.now(timezone.utc)

    next_hour = ((now.hour // 4) + 1) * 4

    if next_hour >= 24:
        target = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=20, microsecond=0
        )
    else:
        target = now.replace(
            hour=next_hour, minute=0, second=20, microsecond=0
        )

    return max(1, (target - now).total_seconds())


async def scheduled_scans(app):
    await asyncio.sleep(seconds_to_next_4h_close())

    while True:
        try:
            await run_scan(app)
        except Exception:
            logging.exception("Scheduled scan failed")

            try:
                await app.bot.send_message(
                    chat_id=cfg.telegram_chat_id,
                    text="⚠️ RTAS: scheduled scan gagal. Cek log."
                )
            except Exception:
                pass

        await asyncio.sleep(4 * 60 * 60)


async def post_init(app):
    if not cfg.telegram_token or not cfg.telegram_chat_id:
        raise RuntimeError(
            "Set TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID."
        )

    await app.bot.send_message(
        chat_id=cfg.telegram_chat_id,
        text="✅ Royandi Trading Alert System aktif."
    )

    if cfg.run_scan_on_start:
        asyncio.create_task(run_scan(app))

    asyncio.create_task(scheduled_scans(app))


async def run_once():
    if not cfg.telegram_token or not cfg.telegram_chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID belum diatur."
        )

    async with Bot(token=cfg.telegram_token) as bot:
        logging.info("RTAS one-time scan started")
        await run_scan(bot)
        logging.info("RTAS one-time scan completed")


def once_main():
    asyncio.run(run_once())


def main():
    if not cfg.telegram_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN belum diisi.")

    app = (
        Application.builder()
        .token(cfg.telegram_token)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("help", help_cmd))

    app.run_polling()


if __name__ == "__main__":
    if "--once" in sys.argv:
        once_main()
    else:
        main()
