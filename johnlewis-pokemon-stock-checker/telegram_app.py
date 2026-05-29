"""Telegram bot: commands + instant stock notifications."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from config_loader import env_poll_interval, load_config, load_products
from monitor import StockMonitor, format_status

logger = logging.getLogger(__name__)


def _get_monitor(context: ContextTypes.DEFAULT_TYPE) -> StockMonitor:
    return context.application.bot_data["monitor"]


def _load_chat_ids(path: Path, default_chat_id: int | None) -> set[int]:
    ids: set[int] = set()
    if default_chat_id is not None:
        ids.add(default_chat_id)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.isdigit():
                ids.add(int(line))
    return ids


def _persist_chat_id(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    path: Path = context.application.bot_data["chats_path"]
    existing = _load_chat_ids(path, None)
    existing.add(chat_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(str(i) for i in sorted(existing)) + "\n", encoding="utf-8")
    monitor = _get_monitor(context)
    monitor.register_chat(chat_id)
    monitor.set_chat_ids(existing)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _persist_chat_id(context, chat_id)
    await update.message.reply_text(
        "John Lewis Pokemon stock checker is active.\n\n"
        "You will get instant alerts when watched items come back in stock.\n\n"
        "Commands:\n"
        "/status — current stock\n"
        "/add &lt;product-url&gt; — watch a product\n"
        "/list — watched products\n"
        "/help — this message",
        parse_mode=ParseMode.HTML,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    monitor = _get_monitor(context)
    snapshots = await monitor.check_now()
    await update.message.reply_text(
        format_status(snapshots),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config_path: Path = context.application.bot_data["config_path"]
    products = load_products(load_config(config_path))
    if not products:
        await update.message.reply_text("No products in config.yaml yet.")
        return
    lines = ["<b>Watched products</b>", ""]
    for product in products:
        lines.append(f"• {_escape(product.name)}")
        lines.append(f"  {product.url}")
        if product.sku:
            lines.append(f"  SKU: {product.sku}")
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /add https://www.johnlewis.com/.../p123456789")
        return

    url = context.args[0].strip()
    if "johnlewis.com" not in url:
        await update.message.reply_text("Please send a johnlewis.com product URL.")
        return

    config_path: Path = context.application.bot_data["config_path"]
    config = load_config(config_path)
    products = config.setdefault("products", [])
    products.append({"name": "Pokemon (added via Telegram)", "url": url, "sku": ""})

    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)

    _persist_chat_id(context, update.effective_chat.id)

    await update.message.reply_text("Added to watchlist. Checking stock now…")
    monitor = _get_monitor(context)
    snapshots = await monitor.check_now()
    await update.message.reply_text(
        format_status(snapshots),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_application(
    *,
    token: str,
    config_path: Path,
    state_path: Path,
    chats_path: Path,
    poll_interval: float,
    default_chat_id: int | None,
) -> Application:
    chat_ids = _load_chat_ids(chats_path, default_chat_id)

    async def post_init(application: Application) -> None:
        async def send(chat_id: int, message: str) -> None:
            await application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.HTML,
            )

        monitor = StockMonitor(
            config_path=config_path,
            state_path=state_path,
            poll_interval=poll_interval,
            notify=send,
        )
        monitor.set_chat_ids(chat_ids)
        application.bot_data["monitor"] = monitor
        application.create_task(monitor.run_loop())

    app = Application.builder().token(token).post_init(post_init).build()

    app.bot_data["config_path"] = config_path
    app.bot_data["chats_path"] = chats_path

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("add", cmd_add))

    return app


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env (create bot via @BotFather)")

    config_path = Path(os.getenv("CONFIG_PATH", "config.yaml"))
    state_path = Path("data/state.json")
    chats_path = Path("data/chat_ids.txt")
    poll_interval = env_poll_interval()

    chat_raw = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    default_chat_id = int(chat_raw) if chat_raw.isdigit() else None

    if not config_path.exists():
        example = Path("config.yaml.example")
        if example.exists():
            config_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            logger.info("Created %s from example — edit it with your product URLs", config_path)

    app = build_application(
        token=token,
        config_path=config_path,
        state_path=state_path,
        chats_path=chats_path,
        poll_interval=poll_interval,
        default_chat_id=default_chat_id,
    )

    logger.info("Starting Telegram bot (poll every %ss)", poll_interval)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
