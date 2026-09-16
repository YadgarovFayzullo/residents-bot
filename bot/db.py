"""SQLite qatlami — arizalar shu yerda saqlanadi (Sheets uchun manba)."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import aiosqlite

# Ariza holatlari
ST_NEW = "new"
ST_FORM = "form"                  # anketa to'ldirilmoqda
ST_RECEIPT_WAIT = "receipt_wait"  # chek kutilmoqda
ST_RECEIPT_SENT = "receipt_sent"  # chek yuborildi, admin tekshirmoqda
ST_STAGE2 = "stage2"
ST_STAGE3 = "stage3"
ST_STAGE4 = "stage4"
ST_DONE = "done"
ST_DECLINED = "declined"

STATUS_LABELS = {
    ST_NEW: "Yangi",
    ST_FORM: "Anketa to‘ldirilmoqda",
    ST_RECEIPT_WAIT: "Chek kutilmoqda",
    ST_RECEIPT_SENT: "Tekshiruvda",
    ST_STAGE2: "2-bosqichda",
    ST_STAGE3: "3-bosqichda",
    ST_STAGE4: "4-bosqichda",
    ST_DONE: "Yakunlandi",
    ST_DECLINED: "Rad etdi",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY,
    tg_username    TEXT,
    full_name      TEXT,
    phone          TEXT,
    username       TEXT,
    receipt_file_id TEXT,
    receipt_type   TEXT,
    receipt_status TEXT DEFAULT 'none',
    receipt_msg_id INTEGER,
    receipt_link   TEXT,
    receipt_at     TEXT,
    reviewed_by    INTEGER,
    reviewed_at    TEXT,
    reject_reason  TEXT,
    agree_stage2   TEXT,
    agree_stage3   TEXT,
    agree_final    TEXT,
    invite_link    TEXT,
    status         TEXT DEFAULT 'new',
    created_at     TEXT,
    updated_at     TEXT,
    finished_at    TEXT,
    sheet_row      INTEGER,
    sheet_synced   INTEGER DEFAULT 0,
    invite_expires TEXT,
    admin_msg_id   INTEGER
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_synced ON users(sheet_synced);
"""

_ALLOWED = {
    "tg_username", "full_name", "phone", "username", "receipt_file_id",
    "receipt_type", "receipt_status", "receipt_msg_id", "receipt_link",
    "receipt_at", "reviewed_by", "reviewed_at",
    "reject_reason", "agree_stage2", "agree_stage3", "agree_final",
    "invite_link", "status", "finished_at", "sheet_row", "sheet_synced",
    "invite_expires", "admin_msg_id",
}


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            # Eski bazalarga yetishmayotgan ustunlarni qo'shamiz
            cur = await db.execute("PRAGMA table_info(users)")
            have = {row[1] for row in await cur.fetchall()}
            for col, ddl in (
                ("invite_expires", "TEXT"),
                ("receipt_msg_id", "INTEGER"),
                ("receipt_link", "TEXT"),
                ("receipt_at", "TEXT"),
                ("admin_msg_id", "INTEGER"),
            ):
                if col not in have:
                    await db.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
            await db.commit()

    # ---------------------------------------------------------- sozlamalar
    async def set_setting(self, key: str, value: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                       value = excluded.value, updated_at = excluded.updated_at""",
                (key, value, now()),
            )
            await db.commit()

    async def get_setting(self, key: str, default: str | None = None) -> str | None:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = await cur.fetchone()
            return row[0] if row else default

    async def ensure_user(self, user_id: int, tg_username: str | None) -> dict[str, Any]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                """INSERT INTO users (user_id, tg_username, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       tg_username = excluded.tg_username,
                       updated_at  = excluded.updated_at""",
                (user_id, tg_username, ST_NEW, now(), now()),
            )
            await db.commit()
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            return dict(row)

    async def get(self, user_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def update(self, user_id: int, **fields: Any) -> dict[str, Any] | None:
        bad = set(fields) - _ALLOWED
        if bad:
            raise ValueError(f"Ruxsat etilmagan ustun(lar): {bad}")
        if not fields:
            return await self.get(user_id)
        # sheet_synced ni qo'lda bermasak, har o'zgarishda 0 ga tushadi
        fields.setdefault("sheet_synced", 0)
        fields["updated_at"] = now()
        sets = ", ".join(f"{k} = ?" for k in fields)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"UPDATE users SET {sets} WHERE user_id = ?",
                (*fields.values(), user_id),
            )
            await db.commit()
        return await self.get(user_id)

    async def reset(self, user_id: int) -> None:
        """Arizani noldan boshlash (yakunlanganlar tegilmaydi)."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """UPDATE users SET full_name=NULL, phone=NULL, username=NULL,
                       receipt_file_id=NULL, receipt_type=NULL, receipt_status='none',
                       receipt_msg_id=NULL, receipt_link=NULL, receipt_at=NULL,
                       reviewed_by=NULL, reviewed_at=NULL, reject_reason=NULL,
                       agree_stage2=NULL, agree_stage3=NULL, agree_final=NULL,
                       status=?, updated_at=?, sheet_synced=0
                   WHERE user_id=? AND status != ?""",
                (ST_FORM, now(), user_id, ST_DONE),
            )
            await db.commit()

    async def delete(self, user_id: int) -> bool:
        """Yozuvni butunlay o'chiradi — ariza noldan boshlanadi."""
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            await db.commit()
            return cur.rowcount > 0

    async def list_by_status(self, status: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM users WHERE status = ? ORDER BY updated_at DESC", (status,)
            )
            return [dict(r) for r in await cur.fetchall()]

    async def search(self, q: str, limit: int = 10) -> list[dict[str, Any]]:
        """ID, ism, telefon yoki username bo'yicha qidiradi."""
        q = q.strip().lstrip("@")
        like = f"%{q}%"
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """SELECT * FROM users
                   WHERE CAST(user_id AS TEXT) = ?
                      OR full_name   LIKE ?
                      OR phone       LIKE ?
                      OR username    LIKE ?
                      OR tg_username LIKE ?
                   ORDER BY updated_at DESC LIMIT ?""",
                (q, like, like, like, like, limit),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def all_users(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users ORDER BY created_at")
            return [dict(r) for r in await cur.fetchall()]

    async def unsynced(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM users WHERE sheet_synced = 0 ORDER BY created_at"
            )
            return [dict(r) for r in await cur.fetchall()]

    async def mark_all_unsynced(self) -> int:
        """Barcha yozuvlarni qayta sinxronlashga belgilaydi (ustunlar o'zgarganda)."""
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("UPDATE users SET sheet_synced = 0")
            await db.commit()
            return cur.rowcount

    async def mark_synced(self, user_id: int, sheet_row: int | None) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE users SET sheet_synced = 1, sheet_row = ? WHERE user_id = ?",
                (sheet_row, user_id),
            )
            await db.commit()

    async def stats(self) -> dict[str, int]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT status, COUNT(*) FROM users GROUP BY status")
            data = {row[0]: row[1] for row in await cur.fetchall()}
            cur = await db.execute("SELECT COUNT(*) FROM users")
            data["total"] = (await cur.fetchone())[0]
            cur = await db.execute(
                "SELECT COUNT(*) FROM users WHERE receipt_status = 'pending'"
            )
            data["pending"] = (await cur.fetchone())[0]
            return data
