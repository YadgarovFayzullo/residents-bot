"""Asoschilar rezidentligi boti — ishga tushirish nuqtasi."""
from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from . import card
from .config import load_config
from .db import Database
from .handlers import admin, group, user
from .middlewares import DepsMiddleware
from .sheets import SheetsSync
from .sync import drain

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot")


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Arizani boshlash"),
            BotCommand(command="status", description="Ariza holati"),
            BotCommand(command="help", description="Yordam"),
        ]
    )


async def main() -> None:
    config = load_config()

    db = Database(config.db_path)
    await db.init()
    log.info("SQLite tayyor: %s", config.db_path)

    sheets = SheetsSync(
        config.sheet_id,
        config.credentials_file,
        config.sheet_name,
        config.sheet_webhook_url,
        config.sheet_webhook_secret,
        config.credentials_json,
    )
    ok, info = await sheets.check()
    log.info("Google Sheets [%s]: %s — %s", sheets.mode,
             "ULANDI" if ok else "ULANMADI", info)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    me = await bot.get_me()
    log.info("Bot: @%s (%s)", me.username, me.id)

    if not config.admin_ids:
        log.warning("ADMIN_IDS bo'sh! Cheklarni hech kim tasdiqlay olmaydi. "
                    "/myid buyrug'i bilan ID ni oling va .env ga qo'shing.")
    archive_chat = config.receipt_archive_id or config.admin_group_id
    if archive_chat:
        log.info("Cheklar arxivi: %s%s", archive_chat,
                 "" if config.receipt_archive_id else " (admin guruhi)")
    else:
        log.warning("Chek arxivi sozlanmagan! RECEIPT_ARCHIVE_ID (yoki ADMIN_GROUP_ID) "
                    "ni .env ga qo'shing — aks holda cheklarga havola saqlanmaydi.")

    if config.admin_group_id:
        log.info("Ariza kartochkalari: %s", config.admin_group_id)
    else:
        log.warning("ADMIN_GROUP_ID bo'sh — ariza kartochkalari yuborilmaydi.")

    saved_group = await db.get_setting("private_group_id")
    if not config.private_group_id and not saved_group:
        log.warning("Yopiq guruh ulanmagan. Botni guruhga qo'shib, admin qiling — "
                    "guruh avtomatik ulanadi.")
    else:
        log.info("Yopiq guruh: %s | havola muddati: %s kun",
                 config.private_group_id or saved_group, config.invite_expire_days)

    dp = Dispatcher(storage=MemoryStorage())
    deps = DepsMiddleware(db, sheets, config)
    dp.message.middleware(deps)
    dp.callback_query.middleware(deps)
    dp.my_chat_member.middleware(deps)

    # admin birinchi — chek tugmalari (ok:/no:) foydalanuvchi router'idan oldin
    dp.include_router(group.router)
    dp.include_router(admin.router)
    dp.include_router(user.router)

    await set_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Polling boshlandi…")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await drain()          # fondagi Sheets yozuvlari yo'qolmasin
        await card.drain()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot to'xtatildi")
    except RuntimeError as e:
        log.error("%s", e)
        sys.exit(1)
