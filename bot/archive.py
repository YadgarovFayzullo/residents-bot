"""Cheklar arxivi.

Har bir chek yopiq kanalga (yoki admin guruhiga) nusxalanadi va uning
havolasi bazaga hamda Google Sheets'ga yoziladi — shu bois chekni
istalgan vaqtda ochib ko'rish mumkin.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def message_link(chat_id: int | None, message_id: int | None) -> str:
    """Yopiq kanal/guruh xabariga havola: https://t.me/c/<chat>/<msg>."""
    if not chat_id or not message_id:
        return ""
    raw = str(chat_id)
    if not raw.startswith("-100"):
        return ""
    return f"https://t.me/c/{raw[4:]}/{message_id}"


async def send_receipt(bot, chat_id: int, file_id: str, ftype: str,
                       caption: str, markup=None):
    """Chekni (rasm yoki fayl) berilgan chatga yuboradi."""
    if ftype == "photo":
        return await bot.send_photo(chat_id, file_id, caption=caption,
                                    reply_markup=markup)
    return await bot.send_document(chat_id, file_id, caption=caption,
                                   reply_markup=markup)


def archive_caption(user: dict[str, Any], user_id: int, when: str) -> str:
    """Arxiv kanalidagi izoh — keyin qidiruv orqali topish uchun."""
    return (
        "🧾 <b>Chek arxivi</b>\n\n"
        f"👤 {user.get('full_name') or '—'}\n"
        f"📞 {user.get('phone') or '—'}\n"
        f"💬 {user.get('username') or '—'}\n"
        f"🆔 <code>{user_id}</code>\n"
        f"🕒 {when}"
    )
