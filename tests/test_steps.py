"""Har bir qadamda jadvalga yozilishini sinash."""
from __future__ import annotations

import asyncio, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import sync
from bot.db import Database
from bot.handlers import admin as A
from bot.handlers import user as U
from bot.sheets import HEADERS, row_from_user
from tests.fakes import (FakeBot, FakeCallback, FakeMessage, FakePhoto,
                         FakeSheets, FakeState, FakeUser)

PASS = FAIL = 0
USER_ID, ADMIN_ID, ARCHIVE_ID = 1001, 777, -1002233445566


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}" + (f"  {extra}" if extra else ""))
    else:    FAIL += 1; print(f"  ❌ {label}  {extra}")


class Cfg:
    admin_ids = [ADMIN_ID]
    admin_group_id = None
    receipt_archive_id = ARCHIVE_ID
    private_group_id = None
    irshod_url = "https://irshod.uz"
    invite_expire_days = 7
    def is_admin(self, uid): return uid in self.admin_ids


def status_of(sh):
    """Soxta jadvaldagi «Ariza holati» ustuni."""
    u = sh.rows.get(USER_ID)
    return None if u is None else row_from_user(u, 1)[HEADERS.index("Ariza holati")]


async def main():
    db = Database(tempfile.mktemp(suffix=".db")); await db.init()
    sh, bot, cfg = FakeSheets(), FakeBot(), Cfg()
    me = FakeUser(USER_ID)
    D = dict(db=db, sheets=sh, bot=bot, config=cfg)
    st = FakeState()

    print("\n【1】 /start — foydalanuvchi darhol jadvalga tushadi")
    await U.cmd_start(FakeMessage(user=me, text="/start"), st, **D)
    await sync.drain()
    check("qator yaratildi", USER_ID in sh.rows)
    check("holat = Yangi", status_of(sh) == "Yangi", f"-> {status_of(sh)}")

    print("\n【2】 Anketa boshlandi")
    await U.cb_start_form(FakeCallback("start_form", user=me), st, db=db, sheets=sh)
    await sync.drain()
    check("holat = Anketa to‘ldirilmoqda",
          status_of(sh) == "Anketa to‘ldirilmoqda", f"-> {status_of(sh)}")

    print("\n【3】 Ism — to‘xtagan joyi ko‘rinadi")
    await U.got_full_name(FakeMessage(user=me, text="Ali Valiyev"), st, db=db, sheets=sh)
    await sync.drain()
    check("ism jadvalda", sh.rows[USER_ID]["full_name"] == "Ali Valiyev")
    check("telefon hali bo‘sh", not sh.rows[USER_ID]["phone"])

    print("\n【4】 Telefon")
    await U.got_phone_text(FakeMessage(user=me, text="+998901234567"), st, db=db, sheets=sh)
    await sync.drain()
    check("telefon jadvalda", sh.rows[USER_ID]["phone"] == "+998901234567",
          f"-> {sh.rows[USER_ID]['phone']}")

    print("\n【5】 Username → chek kutilmoqda")
    await U.got_username_text(FakeMessage(user=me, text="@aliuz"), st, **D)
    await sync.drain()
    check("username jadvalda", sh.rows[USER_ID]["username"] == "@aliuz")
    check("holat = Chek kutilmoqda", status_of(sh) == "Chek kutilmoqda",
          f"-> {status_of(sh)}")

    print("\n【6】 Chek yuborildi")
    st.state = U.Form.receipt
    await U.got_receipt(FakeMessage(user=me, photo=[FakePhoto("F1")]), st, **D)
    await sync.drain()
    check("holat = Tekshiruvda", status_of(sh) == "Tekshiruvda", f"-> {status_of(sh)}")
    check("arxiv havolasi jadvalda", "t.me/c/" in (sh.rows[USER_ID]["receipt_link"] or ""))

    print("\n【7】 Admin tasdiqladi → 2-bosqich")
    await A.cb_approve(FakeCallback(f"ok:{USER_ID}", user=FakeUser(ADMIN_ID)), **D)
    await sync.drain()
    check("holat = 2-bosqichda", status_of(sh) == "2-bosqichda", f"-> {status_of(sh)}")

    print("\n【8】 Har bosqichda jadval yangilanadi")
    for stage, want in ((2, "3-bosqichda"), (3, "4-bosqichda")):
        await U.cb_agree(FakeCallback(f"agree:{stage}", user=me), **D)
        await sync.drain()
        check(f"{stage}-bosqich rozilik → {want}", status_of(sh) == want,
              f"-> {status_of(sh)}")

    print("\n【9】 Rad etgan foydalanuvchi ham ko‘rinadi")
    await U.cb_decline(FakeCallback("decline:4", user=me), **D)
    await sync.drain()
    check("holat = Rad etdi", status_of(sh) == "Rad etdi", f"-> {status_of(sh)}")

    print("\n【10】 «Oxirgi harakat» ustuni to‘ladi")
    row = row_from_user(sh.rows[USER_ID], 1)
    check("ustun mavjud", "Oxirgi harakat" in HEADERS)
    check("vaqt yozilgan", bool(row[HEADERS.index("Oxirgi harakat")]),
          f"-> {row[HEADERS.index('Oxirgi harakat')]}")

    print("\n【11】 Sheets o‘chirilgan bo‘lsa bot yiqilmaydi")
    off = FakeSheets(enabled=False)
    sync.push(db, off, await db.get(USER_ID))
    await sync.drain()
    check("yozuv urinishi bo‘lmadi", off.calls == 0)

    print("\n" + "=" * 60)
    print(f"NATIJA:  ✅ {PASS} ta o'tdi   ❌ {FAIL} ta xato")
    print("=" * 60)
    return FAIL


sys.exit(asyncio.run(main()))
