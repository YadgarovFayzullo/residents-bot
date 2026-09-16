"""Har bir qadamda Google Sheets'ga yozish.

Yozuv fon rejimida ketadi — foydalanuvchi javobni kutib turmaydi.
Shu bois jadvalda ariza qaysi bosqichda to'xtagani darhol ko'rinadi.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

log = logging.getLogger(__name__)

# Task'lar garbage collector tomonidan o'chib ketmasligi uchun ushlab turamiz
_tasks: set[asyncio.Task] = set()


async def _write(db, sheets, user: dict[str, Any]) -> None:
    row = await sheets.upsert(user)
    if row is None:
        return  # xato sheets.last_error da; yozuv sheet_synced=0 bo'lib qoladi
    # webhook rejimida qator raqami noma'lum (-1) — eskisini saqlaymiz
    await db.mark_synced(user["user_id"], row if row > 0 else user.get("sheet_row"))


def push(db, sheets, user: dict[str, Any] | None) -> None:
    """Foydalanuvchini jadvalga yozishni fon rejimida boshlaydi."""
    if not user or not user.get("user_id") or not sheets.enabled:
        return
    task = asyncio.create_task(_write(db, sheets, dict(user)))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def drain(timeout: float = 15.0) -> None:
    """Fondagi barcha yozuvlar tugashini kutadi (to'xtatishdan oldin)."""
    if not _tasks:
        return
    done, pending = await asyncio.wait(set(_tasks), timeout=timeout)
    if pending:
        log.warning("%s ta Sheets yozuvi ulgurmadi", len(pending))


async def push_now(db, sheets, user: dict[str, Any] | None) -> int | None:
    """Xuddi shu narsa, lekin kutib turadi (yakuniy bosqichlar uchun)."""
    if not user or not user.get("user_id") or not sheets.enabled:
        return None
    row = await sheets.upsert(user)
    if row is not None:
        await db.mark_synced(user["user_id"], row if row > 0 else user.get("sheet_row"))
    return row
