"""/reset — arizani noldan boshlash (test hisoblari uchun).

Asosiy holat: yakunlagan odamni ham tozalay olishi kerak. Oddiy /start
buni uddalamaydi, chunki db.reset() «done» holatidagilarga tegmaydi.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.db import Database                                   # noqa: E402
from bot.handlers import admin as A                           # noqa: E402
from bot.handlers import user as U                            # noqa: E402
from fakes import (FakeBot, FakeMessage, FakeSheets,          # noqa: E402
                   FakeState, FakeUser)

ADMIN_ID = 7001
ADMIN_GROUP = -5562057451
PASS = FAIL = 0


class Cfg:
    admin_ids = [ADMIN_ID]
    admin_group_id = ADMIN_GROUP
    receipt_archive_id = None
    private_group_id = -5468472102
    irshod_url = "https://irshod.uz"
    invite_expire_days = 7

    def is_admin(self, uid):
        return uid in self.admin_ids


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}" + (f"  {extra}" if extra else ""))
    else:
        FAIL += 1
        print(f"  ❌ {label}  {extra}")


async def run():
    db = Database(tempfile.mktemp(suffix=".db"))
    await db.init()
    bot, sheets, cfg = FakeBot(), FakeSheets(), Cfg()
    D = dict(db=db, sheets=sheets, bot=bot, config=cfg)

    # Arizani yakunlagan odam + admin guruhidagi kartochkasi
    await db.ensure_user(8192361257, "oxunjon")
    await db.update(8192361257, full_name="Oxunjon Madaminjonov",
                    phone="+998941129502", username="@oxunjon",
                    status="done", invite_link="https://t.me/+OLD",
                    admin_msg_id=4242)

    print("\n【1】 Oddiy /start yakunlaganni tozalamaydi")
    await db.reset(8192361257)
    rec = await db.get(8192361257)
    check("yozuv o‘chmadi — /reset kerak", rec["status"] == "done", f"-> {rec['status']}")

    print("\n【2】 Oddiy foydalanuvchi /reset qila olmaydi")
    m = FakeMessage("/reset 8192361257", FakeUser(999, "begona"))
    await A.cmd_reset(m, **D)
    check("javob berilmadi", not m.replies)
    check("yozuv joyida", await db.get(8192361257) is not None)

    print("\n【3】 ID ko‘rsatilmasa — yordam matni")
    m = FakeMessage("/reset", FakeUser(ADMIN_ID))
    await A.cmd_reset(m, **D)
    check("yo‘riqnoma chiqdi", "noldan boshlash" in m.replies[-1]["text"])
    check("hech narsa o‘chmadi", await db.get(8192361257) is not None)

    print("\n【4】 Admin /reset qiladi")
    m = FakeMessage("/reset 8192361257", FakeUser(ADMIN_ID))
    await A.cmd_reset(m, **D)
    check("yozuv o‘chdi", await db.get(8192361257) is None)
    check("kartochka ham o‘chdi", (ADMIN_GROUP, 4242) in bot.deleted,
          f"-> {bot.deleted}")
    check("ismi hisobotda", "Oxunjon" in m.replies[-1]["text"])

    print("\n【5】 Endi 1-bosqichdan boshlanadi")
    me = FakeUser(8192361257, "oxunjon")
    m = FakeMessage("/start", me)
    await U.cmd_start(m, FakeState(), **D)
    check("xush kelibsiz matni", "xush kelibsiz" in m.replies[-1]["text"].lower())
    check("eski havola berilmadi", "t.me/+OLD" not in m.replies[-1]["text"])
    rec = await db.get(8192361257)
    check("holat = new", rec["status"] == "new", f"-> {rec['status']}")
    check("ismi tozalandi", not rec["full_name"], f"-> {rec['full_name']}")

    print("\n【6】 Bir nechta ID va yo‘q odam")
    await db.ensure_user(559905450, "oxuntest")
    await db.update(559905450, full_name="Oxun Test", status="receipt_wait")
    m = FakeMessage("/reset 559905450 111222333", FakeUser(ADMIN_ID))
    await A.cmd_reset(m, **D)
    check("bori o‘chdi", await db.get(559905450) is None)
    check("yo‘qi haqida aytildi", "topilmadi" in m.replies[-1]["text"])

    print("\n" + "=" * 60)
    print(f"NATIJA:  ✅ {PASS} ta o'tdi   ❌ {FAIL} ta xato")
    print("=" * 60)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
