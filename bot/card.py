"""Admin guruhidagi ariza kartochkasi.

Har bir foydalanuvchiga bitta xabar to'g'ri keladi va bosqichlar o'tgani
sayin o'sha xabarning o'zi tahrirlanadi. Shu bois bir vaqtda o'nlab ariza
ketayotgan bo'lsa ham lenta aralashib ketmaydi: kim qayerda turgani
har doim o'z kartochkasida ko'rinadi.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .db import STATUS_LABELS

log = logging.getLogger(__name__)

_tasks: set[asyncio.Task] = set()

_RECEIPT = {
    "none": "⏸ yuborilmagan",
    "pending": "⏳ tekshiruvda",
    "approved": "✅ tasdiqlangan",
    "rejected": "❌ rad etilgan",
}


def _agree(value: str | None) -> str:
    """agree_* ustunlari «Ha (sana)» yoki «Yo'q (sana)» ko'rinishida saqlanadi."""
    if not value:
        return "⏸"
    return "✅" if value.startswith("Ha") else "❌"


def render(user: dict[str, Any]) -> str:
    name = user.get("full_name") or "—"
    receipt = _RECEIPT.get(user.get("receipt_status") or "none", "—")
    link = (user.get("receipt_link") or "").strip()
    if link:
        receipt += f' (<a href="{link}">chek</a>)'

    lines = [
        f"📋 <b>Ariza</b> — {name}",
        "",
        f"👤 {name}",
        f"📞 {user.get('phone') or '—'}",
        f"💬 {user.get('username') or '—'}",
        f"🆔 <code>{user.get('user_id')}</code>",
        "",
        f"1️⃣ Ro‘yxatdan o‘tish — {'✅' if user.get('phone') else '⏸'}",
        f"2️⃣ Chek (Playbook) — {receipt}",
        f"3️⃣ 61 kunlik dastur — {_agree(user.get('agree_stage2'))}",
        f"4️⃣ Rezidentlik, 3% — {_agree(user.get('agree_stage3'))}",
        f"5️⃣ Yakuniy rozilik — {_agree(user.get('agree_final'))}",
        "",
        f"📌 <b>Holat:</b> {STATUS_LABELS.get(user.get('status') or 'new', '—')}",
        f"🕒 {user.get('updated_at') or '—'}",
    ]
    if user.get("reject_reason"):
        lines.insert(-2, f"✍️ <b>Rad sababi:</b> {user['reject_reason']}")
    return "\n".join(lines)


async def _refresh(bot, db, chat_id: int, user_id: int) -> None:
    user = await db.get(user_id)
    if not user:
        return
    text = render(user)
    msg_id = user.get("admin_msg_id")

    if msg_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id, text=text,
                disable_web_page_preview=True,
            )
            return
        except Exception as e:
            if "not modified" in str(e):
                return
            # Xabar o'chirilgan yoki topilmadi — yangisini yuboramiz
            log.info("Kartochka tahrirlanmadi (%s): %s", user_id, e)

    try:
        msg = await bot.send_message(chat_id, text, disable_web_page_preview=True)
    except Exception as e:
        log.warning("Kartochka yuborilmadi (%s): %s", user_id, e)
        return
    # sheet_synced ni saqlab qolamiz — aks holda yozuv bekorga qayta sinxronlanadi
    await db.update(
        user_id, admin_msg_id=msg.message_id,
        sheet_synced=user.get("sheet_synced") or 0,
    )


def refresh(bot, db, config, user: dict[str, Any] | None) -> None:
    """Kartochkani fon rejimida yangilaydi — foydalanuvchi kutib turmaydi."""
    if not user or not user.get("user_id") or not config.admin_group_id:
        return
    task = asyncio.create_task(
        _refresh(bot, db, config.admin_group_id, int(user["user_id"]))
    )
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def drain(timeout: float = 10.0) -> None:
    """To'xtashdan oldin yuborilayotgan kartochkalarni kutadi."""
    if not _tasks:
        return
    _, pending = await asyncio.wait(set(_tasks), timeout=timeout)
    if pending:
        log.warning("%s ta kartochka ulgurmadi", len(pending))
