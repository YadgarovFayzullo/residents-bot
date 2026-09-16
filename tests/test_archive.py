"""Chek arxivi: havola saqlanishi va /chek orqali qayta ochilishi."""
from __future__ import annotations

import asyncio, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import archive
from bot.db import Database
from bot.handlers import admin as A
from bot.handlers import user as U
from bot.sheets import HEADERS, row_from_user
from tests.fakes import OUT, FakeBot, FakeMessage, FakePhoto, FakeSheets, FakeState, FakeUser

PASS = FAIL = 0
USER_ID, ADMIN_ID = 1001, 777
ARCHIVE_ID, ADMIN_GROUP = -1002233445566, -1009988776655


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}" + (f"  {extra}" if extra else ""))
    else:    FAIL += 1; print(f"  ❌ {label}  {extra}")


class Cfg:
    admin_ids = [ADMIN_ID]
    admin_group_id = ADMIN_GROUP
    receipt_archive_id = ARCHIVE_ID
    private_group_id = None
    irshod_url = "https://irshod.uz"
    invite_expire_days = 7
    def is_admin(self, uid): return uid in self.admin_ids


async def send_receipt(db, cfg, bot):
    """Foydalanuvchi chek yuboradi."""
    m = FakeMessage(user=FakeUser(USER_ID), photo=[FakePhoto("FILE_ABC")])
    await U.got_receipt(m, FakeState(), db=db, sheets=FakeSheets(),
                        bot=bot, config=cfg)
    return await db.get(USER_ID)


async def main():
    db = Database(tempfile.mktemp(suffix=".db")); await db.init()
    await db.ensure_user(USER_ID, "aliuz")
    await db.update(USER_ID, full_name="Ali Valiyev", phone="+998901234567",
                    username="@aliuz")

    print("\n【1】 Havola formati")
    check("yopiq kanal havolasi",
          archive.message_link(-1002233445566, 42) == "https://t.me/c/2233445566/42")
    check("oddiy chat uchun havola yo'q", archive.message_link(12345, 42) == "")
    check("msg_id bo'lmasa bo'sh", archive.message_link(ARCHIVE_ID, None) == "")

    print("\n【2】 Chek arxivga saqlanadi, tekshiruv faqat kanalda")
    cfg, bot = Cfg(), FakeBot()
    u = await send_receipt(db, cfg, bot)
    check("arxivga yuborildi", any(c == ARCHIVE_ID for c, _ in bot.sent))
    check("kanaldagi nusxada tugmalar bor",
          any(c == ARCHIVE_ID and m is not None for c, m in bot.markups))
    # Tugmalar bitta joyda bo'lsin — botda takror tekshiruv bo'lmasin
    check("adminga shaxsiy nusxa yuborilmadi",
          not any(c == ADMIN_ID for c, _ in bot.sent))
    # Admin guruhida faqat ariza kartochkalari turadi — chek u yerga tushmaydi
    group_files = [t for c, t in bot.sent
                   if c == ADMIN_GROUP and t.startswith(("[PHOTO]", "[DOC]"))]
    check("admin guruhiga chek tushmadi", not group_files, f"-> {group_files}")
    check("message_id saqlandi", bool(u["receipt_msg_id"]), f"-> {u['receipt_msg_id']}")
    check("havola saqlandi", (u["receipt_link"] or "").startswith("https://t.me/c/2233445566/"),
          f"-> {u['receipt_link']}")
    check("chek sanasi saqlandi", bool(u["receipt_at"]), f"-> {u['receipt_at']}")

    print("\n【2b】 Kanal ishlamasa — chek yo'qolmaydi, adminlarga tushadi")

    class BrokenArchiveBot(FakeBot):
        async def send_photo(self, chat_id, *a, **kw):
            if chat_id == ARCHIVE_ID:
                raise RuntimeError("kanalga yuborib bo'lmadi")
            return await super().send_photo(chat_id, *a, **kw)

    db_b = Database(tempfile.mktemp(suffix=".db")); await db_b.init()
    await db_b.ensure_user(USER_ID, "aliuz")
    await db_b.update(USER_ID, full_name="Ali Valiyev", phone="+998901234567")
    bot_b = BrokenArchiveBot()
    ub = await send_receipt(db_b, Cfg(), bot_b)
    check("chek qabul qilindi", ub["receipt_status"] == "pending")
    check("adminga zaxira nusxa ketdi", any(c == ADMIN_ID for c, _ in bot_b.sent))
    check("zaxira nusxada tugmalar bor",
          any(c == ADMIN_ID and m is not None for c, m in bot_b.markups))

    print("\n【3】 Havola Google Sheets qatoriga tushadi")
    row = row_from_user(u, 1)
    col = HEADERS.index("Chek (arxiv)")
    check("ustun mavjud", col > 0)
    check("qatorda havola bor", row[col] == u["receipt_link"], f"-> {row[col]}")
    check("ustunlar soni mos", len(row) == len(HEADERS))

    print("\n【4】 Alohida kanal yo'q — admin guruhi arxiv bo'ladi")
    class Cfg2(Cfg):
        receipt_archive_id = None
    db2 = Database(tempfile.mktemp(suffix=".db")); await db2.init()
    await db2.ensure_user(USER_ID, "aliuz")
    await db2.update(USER_ID, full_name="Bek", phone="+998901112233", username="@bek")
    bot2 = FakeBot()
    u2 = await send_receipt(db2, Cfg2(), bot2)
    check("kanalga yuborilmadi", not any(c == ARCHIVE_ID for c, _ in bot2.sent))
    check("guruh xabari arxiv bo'ldi",
          (u2["receipt_link"] or "").startswith("https://t.me/c/9988776655/"),
          f"-> {u2['receipt_link']}")

    print("\n【5】 Arxiv umuman yo'q — bot yiqilmaydi")
    class Cfg3(Cfg):
        receipt_archive_id = None
        admin_group_id = None
    db3 = Database(tempfile.mktemp(suffix=".db")); await db3.init()
    await db3.ensure_user(USER_ID, "aliuz")
    u3 = await send_receipt(db3, Cfg3(), FakeBot())
    check("chek baribir qabul qilindi", u3["receipt_status"] == "pending")
    check("havola bo'sh", not u3["receipt_link"])

    print("\n【6】 /chek bilan qidirish")
    for q, label in ((str(USER_ID), "ID bo'yicha"), ("Ali", "ism bo'yicha"),
                     ("901234567", "telefon bo'yicha"), ("@aliuz", "username bo'yicha")):
        rows = await db.search(q)
        check(f"topildi — {label}", len(rows) == 1 and rows[0]["user_id"] == USER_ID)
    check("yo'q narsa topilmadi", await db.search("Xoja Nasriddin") == [])

    print("\n【7】 /chek chekni qayta yuboradi")
    bot4 = FakeBot()
    m = FakeMessage(user=FakeUser(ADMIN_ID), text=f"/chek {USER_ID}")
    await A.cmd_chek(m, db=db, bot=bot4, config=cfg)
    sent = [txt for c, txt in bot4.sent if c == m.chat.id]
    check("chek yuborildi", len(sent) == 1, f"-> {len(sent)} ta")
    check("izohda arxiv havolasi bor", "t.me/c/" in (sent[0] if sent else ""))
    bot5 = FakeBot()
    await A.cmd_chek(FakeMessage(user=FakeUser(999), text=f"/chek {USER_ID}"),
                     db=db, bot=bot5, config=cfg)
    check("oddiy foydalanuvchiga berilmadi", not bot5.sent)

    print("\n" + "=" * 60)
    print(f"NATIJA:  ✅ {PASS} ta o'tdi   ❌ {FAIL} ta xato")
    print("=" * 60)
    return FAIL


sys.exit(asyncio.run(main()))
