"""Bot konfiguratsiyasi (.env fayldan o'qiladi)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# SSL sertifikat sozlamasi bot/__init__.py da — aiohttp import qilinishidan oldin.


def _ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    out = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            out.append(int(part))
    return out


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: list[int] = field(default_factory=list)
    admin_group_id: int | None = None
    receipt_archive_id: int | None = None
    private_group_id: int | None = None
    sheet_id: str = ""
    sheet_name: str = "Arizalar"
    sheet_webhook_url: str = ""
    sheet_webhook_secret: str = ""
    credentials_file: Path = BASE_DIR / "credentials.json"
    credentials_json: str = ""
    db_path: Path = BASE_DIR / "data" / "bot.db"
    irshod_url: str = "https://irshod.uz"
    invite_expire_days: int = 7

    @property
    def sheets_enabled(self) -> bool:
        if self.sheet_webhook_url:
            return True
        if not self.sheet_id:
            return False
        return bool(self.credentials_json) or self.credentials_file.exists()

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN .env faylda ko'rsatilmagan")

    group_raw = os.getenv("ADMIN_GROUP_ID", "").strip()
    private_raw = os.getenv("PRIVATE_GROUP_ID", "").strip()
    archive_raw = os.getenv("RECEIPT_ARCHIVE_ID", "").strip()

    return Config(
        bot_token=token,
        admin_ids=_ids(os.getenv("ADMIN_IDS")),
        admin_group_id=int(group_raw) if group_raw.lstrip("-").isdigit() else None,
        receipt_archive_id=int(archive_raw) if archive_raw.lstrip("-").isdigit() else None,
        private_group_id=int(private_raw) if private_raw.lstrip("-").isdigit() else None,
        sheet_id=os.getenv("SHEET_ID", "").strip(),
        sheet_name=os.getenv("SHEET_NAME", "Arizalar").strip() or "Arizalar",
        sheet_webhook_url=os.getenv("SHEET_WEBHOOK_URL", "").strip(),
        sheet_webhook_secret=os.getenv("SHEET_WEBHOOK_SECRET", "").strip(),
        credentials_file=Path(
            os.getenv("GOOGLE_CREDENTIALS_FILE", str(BASE_DIR / "credentials.json"))
        ),
        credentials_json=os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip(),
        db_path=Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "bot.db"))),
        irshod_url=os.getenv("IRSHOD_URL", "https://irshod.uz").strip(),
        invite_expire_days=max(1, int(os.getenv("INVITE_EXPIRE_DAYS", "7") or 7)),
    )
