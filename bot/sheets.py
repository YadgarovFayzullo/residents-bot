"""Google Sheets sinxronizatsiyasi.

Credentials bo'lmasa bot baribir ishlaydi — yozuvlar SQLite'da to'planib turadi
va keyinroq /sync buyrug'i bilan jadvalga ko'chiriladi.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from . import ca_bundle
from .db import STATUS_LABELS

log = logging.getLogger(__name__)

HEADERS = [
    "№",
    "Telegram ID",
    "Ism familiya",
    "Telefon",
    "Username",
    "Ro‘yxatdan o‘tgan sana",
    "Chek holati",
    "Chek sanasi",
    "Chek (arxiv)",
    "Tekshirgan admin",
    "Rad etish sababi",
    "2-bosqich rozilik",
    "3-bosqich rozilik",
    "Yakuniy rozilik",
    "Ariza holati",
    "Yakunlangan sana",
    "Taklif havolasi",
    "Oxirgi harakat",
]

RECEIPT_LABELS = {
    "none": "Yuborilmagan",
    "pending": "Tekshiruvda",
    "approved": "Tasdiqlangan",
    "rejected": "Rad etilgan",
}


def _receipt_cell(u: dict[str, Any]) -> str:
    """Arxiv kanalidagi chekka havola (bosilsa — chek ochiladi)."""
    link = (u.get("receipt_link") or "").strip()
    if link:
        return link
    return "—" if not u.get("receipt_file_id") else "arxivsiz"


def row_from_user(u: dict[str, Any], index: int) -> list[str]:
    """Bitta foydalanuvchini jadval qatoriga aylantiradi."""
    return [
        str(index),
        str(u.get("user_id") or ""),
        u.get("full_name") or "",
        u.get("phone") or "",
        u.get("username") or (f"@{u['tg_username']}" if u.get("tg_username") else ""),
        u.get("created_at") or "",
        RECEIPT_LABELS.get(u.get("receipt_status") or "none", "—"),
        u.get("receipt_at") or u.get("reviewed_at") or "",
        _receipt_cell(u),
        str(u.get("reviewed_by") or ""),
        u.get("reject_reason") or "",
        u.get("agree_stage2") or "",
        u.get("agree_stage3") or "",
        u.get("agree_final") or "",
        STATUS_LABELS.get(u.get("status") or "new", u.get("status") or ""),
        u.get("finished_at") or "",
        u.get("invite_link") or "",
        u.get("updated_at") or "",
    ]


class SheetsSync:
    """Ikki xil usulni qo'llab-quvvatlaydi:

    1. webhook  — Apps Script (oddiy, credentials kerak emas)
    2. service  — service account + credentials.json
    """

    def __init__(
        self,
        sheet_id: str,
        credentials_file: Path,
        worksheet_name: str,
        webhook_url: str = "",
        webhook_secret: str = "",
        credentials_json: str = "",
    ):
        self.sheet_id = sheet_id
        self.credentials_file = Path(credentials_file)
        self.worksheet_name = worksheet_name
        self.webhook_url = (webhook_url or "").strip()
        self.webhook_secret = webhook_secret or ""
        # Fayl joylay olmaydigan muhitlar uchun (Railway va h.k.)
        self.credentials_json = (credentials_json or "").strip()
        self._ws = None
        self._lock = asyncio.Lock()
        self.last_error: str | None = None

    @property
    def has_credentials(self) -> bool:
        return bool(self.credentials_json) or self.credentials_file.exists()

    @property
    def mode(self) -> str:
        if self.webhook_url:
            return "webhook"
        if self.sheet_id and self.has_credentials:
            return "service"
        return "off"

    @property
    def enabled(self) -> bool:
        return self.mode != "off"

    # ------------------------------------------------------------ webhook
    @staticmethod
    def _connector():
        """Qo'shimcha CA fayli bo'lsa, uni aniq ishlatadigan connector."""
        import aiohttp

        bundle = ca_bundle()
        if not bundle:
            return None
        import ssl

        return aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=bundle))

    async def _post(self, rows: list[list[str]]) -> dict:
        import aiohttp

        payload = {
            "secret": self.webhook_secret,
            "headers": HEADERS,
            "rows": rows,
        }
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(
            timeout=timeout, connector=self._connector()
        ) as session:
            async with session.post(self.webhook_url, json=payload) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}: {text[:200]}")
                try:
                    data = json.loads(text)
                except ValueError:
                    raise RuntimeError(f"JSON emas: {text[:200]}") from None
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "noma'lum xato"))
        return data

    # ---------------------------------------------------------- ichki (sync)
    def _connect(self):
        if self._ws is not None:
            return self._ws
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        if self.credentials_json:
            creds = Credentials.from_service_account_info(
                json.loads(self.credentials_json), scopes=scopes
            )
        else:
            creds = Credentials.from_service_account_file(
                str(self.credentials_file), scopes=scopes
            )
        client = gspread.authorize(creds)
        book = client.open_by_key(self.sheet_id)
        try:
            ws = book.worksheet(self.worksheet_name)
        except Exception:
            ws = book.add_worksheet(
                title=self.worksheet_name, rows=1000, cols=len(HEADERS)
            )
        # Sarlavhalarni tekshirib/qo'yib chiqamiz
        current = ws.row_values(1)
        if current != HEADERS:
            ws.update(values=[HEADERS], range_name=f"A1:{_col(len(HEADERS))}1")
            ws.format(
                f"A1:{_col(len(HEADERS))}1",
                {
                    "textFormat": {"bold": True},
                    "backgroundColor": {"red": 0.16, "green": 0.5, "blue": 0.73},
                    "horizontalAlignment": "CENTER",
                },
            )
            ws.freeze(rows=1)
        self._ws = ws
        return ws

    def _find_row(self, ws, user_id: int) -> int | None:
        ids = ws.col_values(2)  # B ustuni — Telegram ID
        target = str(user_id)
        for i, value in enumerate(ids[1:], start=2):
            if value.strip() == target:
                return i
        return None

    def _upsert(self, user: dict[str, Any]) -> int:
        ws = self._connect()
        user_id = int(user["user_id"])
        row_no = user.get("sheet_row")
        # Kesh ishonchli emas — ID mos kelishini tekshiramiz
        if row_no:
            try:
                if ws.cell(int(row_no), 2).value != str(user_id):
                    row_no = None
            except Exception:
                row_no = None
        if not row_no:
            row_no = self._find_row(ws, user_id)

        if row_no:
            values = row_from_user(user, row_no - 1)
            ws.update(
                values=[values],
                range_name=f"A{row_no}:{_col(len(HEADERS))}{row_no}",
                value_input_option="USER_ENTERED",
            )
            return row_no

        next_row = len(ws.col_values(2)) + 1
        if next_row < 2:
            next_row = 2
        values = row_from_user(user, next_row - 1)
        ws.update(
            values=[values],
            range_name=f"A{next_row}:{_col(len(HEADERS))}{next_row}",
            value_input_option="USER_ENTERED",
        )
        return next_row

    # ------------------------------------------------------------ ommaviy
    async def upsert(self, user: dict[str, Any]) -> int | None:
        """Foydalanuvchini jadvalga yozadi. Qator raqamini qaytaradi."""
        if not self.enabled:
            return None
        async with self._lock:
            try:
                if self.mode == "webhook":
                    await self._post([row_from_user(user, 0)])
                    row = int(user.get("sheet_row") or 0) or -1
                else:
                    row = await asyncio.to_thread(self._upsert, user)
                self.last_error = None
                return row
            except Exception as e:  # tarmoq/kvota xatosi botni to'xtatmasin
                self.last_error = str(e)
                self._ws = None
                log.warning("Sheets yozuv xatosi (user %s): %s", user.get("user_id"), e)
                return None

    async def check(self) -> tuple[bool, str]:
        """Ulanishni tekshiradi — (muvaffaqiyat, xabar)."""
        if self.mode == "webhook":
            try:
                import aiohttp

                timeout = aiohttp.ClientTimeout(total=20)
                async with aiohttp.ClientSession(
                    timeout=timeout, connector=self._connector()
                ) as session:
                    async with session.get(self.webhook_url) as resp:
                        text = await resp.text()
                        if resp.status != 200:
                            return False, f"HTTP {resp.status}"
                data = json.loads(text)
                if data.get("ok"):
                    return True, "Apps Script (webhook) ulandi"
                return False, str(data.get("error"))
            except Exception as e:
                return False, f"webhook javob bermadi: {e}"

        if not self.sheet_id:
            return False, "SHEET_ID .env faylda ko‘rsatilmagan"
        if not self.has_credentials:
            return False, (
                f"Credentials topilmadi: {self.credentials_file} fayli ham, "
                "GOOGLE_CREDENTIALS_JSON o‘zgaruvchisi ham yo‘q"
            )
        try:
            ws = await asyncio.to_thread(self._connect)
            title = await asyncio.to_thread(lambda: ws.spreadsheet.title)
            rows = await asyncio.to_thread(lambda: len(ws.col_values(2)))
            return True, f"«{title}» → «{self.worksheet_name}», {max(rows - 1, 0)} ta yozuv"
        except Exception as e:
            return False, str(e)


def _col(n: int) -> str:
    """1 -> A, 27 -> AA"""
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s
