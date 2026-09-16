"""Har bir handler'ga db/sheets/config ni uzatuvchi middleware."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class DepsMiddleware(BaseMiddleware):
    def __init__(self, db, sheets, config):
        self.db = db
        self.sheets = sheets
        self.config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["db"] = self.db
        data["sheets"] = self.sheets
        data["config"] = self.config
        return await handler(event, data)
