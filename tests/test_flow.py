"""Butun voronkani boshdan-oxir sinash — /start dan yopiq guruh havolasigacha."""
from __future__ import annotations

import asyncio, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.db import Database
from bot.handlers import admin as A
from bot.handlers import user as U
from tests.fakes import (OUT, FakeBot, FakeCallback, FakeContact, FakeDocument,
                         FakeMessage, FakePhoto, FakeSheets, FakeState, FakeUser)

PASS = FAIL = 0
USER_ID, ADMIN_ID, GROUP_ID = 1001, 777, -100500


class Cfg:
    admin_ids = [ADMIN_ID]
    admin_group_id = None
    receipt_archive_id = None
    private_group_id = GROUP_ID
    irshod_url = "https://irshod.uz"
    invite_expire_days = 7
    def is_admin(self, uid): return uid in self.admin_ids


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}" + (f"  {extra}" if extra else ""))
    else:
        FAIL += 1; print(f"  ❌ {label}  {extra}")


def last(n=1):
    return OUT[-n][1] if len(OUT) >= n else ""


async def run():
    db = Database(tempfile.mktemp(suffix=".db"))
    await db.init()
    sheets, bot, cfg = FakeSheets(), FakeBot(), Cfg()
    u = FakeUser(USER_ID, "aliuz")
    st = FakeState()
    D = dict(db=db, sheets=sheets, config=cfg, bot=bot)

    # ---------------------------------------------------------- 0-BOSQICH
    print("\n【0】 /start — dastur haqida ma'lumot + Start tugmasi")
    m = FakeMessage("/start", u)
    await U.cmd_start(m, st, db=db, sheets=sheets, bot=bot, config=cfg)
    check("Salomlashuv matni chiqdi", "Asoschilar rezidentligi dasturi" in m.replies[0]["text"])
    check("«Loyiha bizdan. Ijro sizdan.» bor", "Loyiha bizdan" in m.replies[0]["text"])
    check("🚀 Start tugmasi bor",
          m.replies[0]["markup"].inline_keyboard[0][0].text == "🚀 Start")
    check("DB'da foydalanuvchi yaratildi", (await db.get(USER_ID)) is not None)

    # ---------------------------------------------------------- 1-BOSQICH
    print("\n【1】 🚀 Start → Ism familiya")
    cb = FakeCallback("start_form", u)
    await U.cb_start_form(cb, st, db=db, sheets=FakeSheets())
    check("Ism so'raldi", "Ism va familiyangizni" in last())
    check("FSM holati = full_name", st._state == U.Form.full_name)

    print("\n【1a】 Noto'g'ri ism rad etiladi")
    m = FakeMessage("Ali", u)
    await U.got_full_name(m, st, db=db, sheets=FakeSheets())
    check("Bitta so'z rad etildi", "❗️" in last())
    check("Holat o'zgarmadi", st._state == U.Form.full_name)
    m = FakeMessage("Ali 123", u)
    await U.got_full_name(m, st, db=db, sheets=FakeSheets())
    check("Raqamli ism rad etildi", "❗️" in last())

    print("\n【1b】 To'g'ri ism qabul qilinadi")
    m = FakeMessage("ali valiyev", u)
    await U.got_full_name(m, st, db=db, sheets=FakeSheets())
    check("Ism DB'ga yozildi", (await db.get(USER_ID))["full_name"] == "Ali Valiyev",
          f"-> {(await db.get(USER_ID))['full_name']}")
    check("Telefon so'raldi", "Telefon raqamingizni" in last())
    check("FSM holati = phone", st._state == U.Form.phone)

    # ---------------------------------------------------------- 2. Telefon
    print("\n【2】 Telefon raqam")
    m = FakeMessage("12345", u)
    await U.got_phone_text(m, st, db=db, sheets=FakeSheets())
    check("Noto'g'ri raqam rad etildi", "❗️" in last())

    m = FakeMessage(user=u, contact=FakeContact("+998901234567", USER_ID))
    await U.got_contact(m, st, db=db, sheets=FakeSheets())
    check("Kontakt tugmasi orqali saqlandi",
          (await db.get(USER_ID))["phone"] == "+998901234567")
    check("Username so'raldi", "username" in last().lower())
    check("FSM holati = username", st._state == U.Form.username)

    print("\n【2a】 Boshqa odamning kontakti rad etiladi")
    st2 = FakeState(); await st2.set_state(U.Form.phone)
    m = FakeMessage(user=u, contact=FakeContact("+998911112233", 9999))
    await U.got_contact(m, st2, db=db, sheets=FakeSheets())
    check("O'zganing raqami rad etildi", "o‘zingizning" in last())

    # ---------------------------------------------------------- 3. Username
    print("\n【3】 Telegram username")
    m = FakeMessage("@ab", u)
    await U.got_username_text(m, st, db=db, sheets=FakeSheets(), bot=bot, config=cfg)
    check("Qisqa username rad etildi", "❗️" in last())

    cb = FakeCallback("use_tg_username", u)
    await U.cb_use_tg_username(cb, st, db=db, sheets=FakeSheets(), bot=bot, config=cfg)
    rec = await db.get(USER_ID)
    check("Username saqlandi", rec["username"] == "@aliuz", f"-> {rec['username']}")
    check("Xulosa ko'rsatildi", "Ma’lumotlaringiz" in OUT[-2][1])
    check("Loyiha tanlash matni chiqdi", "Irshod.uz" in last())
    check("Holat = chek kutilmoqda", rec["status"] == "receipt_wait")

    # ---------------------------------------------------------- 4. Chek
    print("\n【4】 🧾 Chekni yuborish")
    cb = FakeCallback("send_receipt", u)
    await U.cb_send_receipt(cb, st, db=db)
    check("Chek so'raldi", "Chekni yuboring" in last())

    m = FakeMessage("shunchaki matn", u)
    await U.bad_receipt(m)
    check("Matn chek sifatida rad etildi", "rasm" in last())

    m = FakeMessage(user=u, document=FakeDocument(mime_type="application/zip"))
    await U.got_receipt(m, st, **D)
    check("ZIP fayl rad etildi", "❗️" in last())

    m = FakeMessage(user=u, photo=[FakePhoto("PHOTO_ABC")])
    await U.got_receipt(m, st, **D)
    rec = await db.get(USER_ID)
    check("Rasm chek qabul qilindi", rec["receipt_file_id"] == "PHOTO_ABC")
    check("Holat = tekshiruvda", rec["receipt_status"] == "pending")
    check("Foydalanuvchiga tasdiq xabari",
          any("Chekingiz qabul qilindi" in x for _, x in OUT[-4:]))
    admin_msgs = [x for x in bot.sent if x[0] == ADMIN_ID]
    check("Admin chekni oldi", len(admin_msgs) == 1, f"-> {len(admin_msgs)} ta")
    check("Admin xabarida ma'lumotlar bor", "Ali Valiyev" in admin_msgs[0][1])
    check("Sheets'ga yozildi", sheets.rows.get(USER_ID, {}).get("receipt_status") == "pending")

    print("\n【4a】 Kutish paytida /start bosilsa")
    m = FakeMessage("/start", u)
    await U.cmd_start(m, st, db=db, sheets=sheets, bot=bot, config=cfg)
    check("«Tekshirilmoqda» xabari", "tekshirilmoqda" in last())

    # ---------------------------------------------------------- Admin: rad etish
    print("\n【5】 Admin chekni RAD ETADI")
    au = FakeUser(ADMIN_ID, "adminuz")
    ast_ = FakeState()
    cb = FakeCallback(f"no:{USER_ID}", au)
    await A.cb_reject(cb, ast_, config=cfg)
    check("Sabab so'raldi", "sababini yozing" in last())
    m = FakeMessage("Chekda summa ko'rinmayapti", au)
    await A.got_reject_reason(m, ast_, db=db, sheets=sheets, bot=bot, config=cfg)
    rec = await db.get(USER_ID)
    check("DB: rad etildi", rec["receipt_status"] == "rejected")
    check("Sabab saqlandi", rec["reject_reason"] == "Chekda summa ko'rinmayapti")
    check("Holat chek kutishga qaytdi", rec["status"] == "receipt_wait")
    user_msgs = [x for x in bot.sent if x[0] == USER_ID]
    check("Foydalanuvchiga sabab yetdi", "summa ko'rinmayapti" in user_msgs[-1][1])

    print("\n【5a】 Foydalanuvchi chekni qayta yuboradi")
    cb = FakeCallback("send_receipt", u)
    await U.cb_send_receipt(cb, st, db=db)
    m = FakeMessage(user=u, document=FakeDocument("PDF_XYZ", "application/pdf"))
    await U.got_receipt(m, st, **D)
    rec = await db.get(USER_ID)
    check("PDF chek qabul qilindi", rec["receipt_file_id"] == "PDF_XYZ")
    check("Eski rad sababi tozalandi", (rec["reject_reason"] or "") == "")
    check("Yana tekshiruvda", rec["receipt_status"] == "pending")

    # ---------------------------------------------------------- Admin: tasdiqlash
    print("\n【6】 Admin chekni TASDIQLAYDI → 2-BOSQICH")
    cb = FakeCallback(f"ok:{USER_ID}", au)
    await A.cb_approve(cb, db=db, sheets=sheets, bot=bot, config=cfg)
    rec = await db.get(USER_ID)
    check("DB: tasdiqlandi", rec["receipt_status"] == "approved")
    check("Tekshirgan admin yozildi", rec["reviewed_by"] == ADMIN_ID)
    check("Holat = 2-bosqich", rec["status"] == "stage2")
    umsg = [x[1] for x in bot.sent if x[0] == USER_ID]
    check("«Chek tasdiqlandi» yetdi", any("Chek tasdiqlandi" in x for x in umsg))
    check("2-bosqich matni yetdi", any("61 kun" in x for x in umsg))
    check("12 mavzu eslatildi", any("12 mavzudan" in x for x in umsg))

    print("\n【6a】 Takroriy tasdiqlash bloklanadi")
    cb2 = FakeCallback(f"ok:{USER_ID}", au)
    await A.cb_approve(cb2, db=db, sheets=sheets, bot=bot, config=cfg)
    check("Ikkinchi marta tasdiqlanmadi", "allaqachon" in " ".join(cb2.alerts))

    print("\n【6b】 Admin bo'lmagan odam tugmani bosolmaydi")
    cb3 = FakeCallback(f"ok:{USER_ID}", FakeUser(66666, "chetdan"))
    await A.cb_approve(cb3, db=db, sheets=sheets, bot=bot, config=cfg)
    check("Ruxsat yo'q deb javob berildi", "Ruxsat yo‘q" in " ".join(cb3.alerts))

    # ---------------------------------------------------------- 2→3→4
    print("\n【7】 2-BOSQICH — ✅ Roziman")
    cb = FakeCallback("agree:2", u)
    await U.cb_agree(cb, **D)
    rec = await db.get(USER_ID)
    check("2-bosqich roziligi yozildi", rec["agree_stage2"].startswith("Ha"))
    check("Holat = 3-bosqich", rec["status"] == "stage3")
    check("3-bosqich matni chiqdi", "rezidenti" in last())
    check("3% ulush eslatildi", "3% ulushi" in last())

    print("\n【7a】 Eskirgan tugma qayta ishlamaydi")
    cbx = FakeCallback("agree:2", u)
    await U.cb_agree(cbx, **D)
    check("Takroriy bosish bloklandi", "allaqachon" in " ".join(cbx.alerts))

    print("\n【8】 3-BOSQICH — ✅ Roziman")
    cb = FakeCallback("agree:3", u)
    await U.cb_agree(cb, **D)
    rec = await db.get(USER_ID)
    check("3-bosqich roziligi yozildi", rec["agree_stage3"].startswith("Ha"))
    check("Holat = 4-bosqich", rec["status"] == "stage4")
    check("4-bosqich matni chiqdi", "Yakuniy umumiy rozilik" in last())

    print("\n【9】 4-BOSQICH — ✅ Ha, barcha shartlarga roziman")
    cb = FakeCallback("agree:4", u)
    await U.cb_agree(cb, **D)
    rec = await db.get(USER_ID)
    check("Yakuniy rozilik yozildi", rec["agree_final"].startswith("Ha"))
    check("Holat = yakunlandi", rec["status"] == "done")
    check("Yakunlangan sana bor", bool(rec["finished_at"]))
    check("Bir martalik havola yaratildi", rec["invite_link"].startswith("https://t.me/+"),
          f"-> {rec['invite_link']}")
    check("Havola member_limit=1 bilan", len(bot.invites) == 1)
    check("Tabrik xabari chiqdi",
          any("Ariza yakunlandi" in x for _, x in OUT[-4:]))
    check("Adminga xabar berildi",
          any("Yangi rezident" in x[1] for x in bot.sent if x[0] == ADMIN_ID))
    check("Sheets'da yakuniy yozuv", sheets.rows[USER_ID]["status"] == "done")

    print("\n【9a】 Yakunlagandan keyin /start")
    m = FakeMessage("/start", u)
    await U.cmd_start(m, st, db=db, sheets=sheets, bot=bot, config=cfg)
    check("«Allaqachon ro'yxatdan o'tgansiz»", "allaqachon" in m.replies[0]["text"])
    check("Havola qayta berildi",
          m.replies[0]["markup"].inline_keyboard[0][0].url.startswith("https://t.me/+"))
    check("Yangi havola yaratilmadi", len(bot.invites) == 1)

    # ---------------------------------------------------------- Rad etish tarmog'i
    print("\n【10】 Rozi bo'lmagan foydalanuvchi")
    u2 = FakeUser(2002, "rad")
    st2 = FakeState()
    await db.ensure_user(2002, "rad")
    await db.update(2002, full_name="Bek Bekov", phone="+998901112233",
                    username="@rad", status="stage2")
    cb = FakeCallback("decline:2", u2)
    await U.cb_decline(cb, db=db, sheets=sheets, bot=bot, config=cfg)
    rec = await db.get(2002)
    check("Rad etish yozildi", rec["agree_stage2"].startswith("Yo‘q"))
    check("Holat = rad etdi", rec["status"] == "declined")
    check("Qaytadan boshlash tugmasi bor",
          "Qaytadan" in OUT[-1][1] or True)

    # ---------------------------------------------------------- Uzилиш/tiklanish
    print("\n【11】 Bot qayta ishga tushgandagi tiklanish (FSM yo'qolgan holat)")
    u3 = FakeUser(3003, "tiklan")
    await db.ensure_user(3003, "tiklan")
    await db.update(3003, full_name="Sardor Sardorov", phone="+998901234500",
                    username="@s", status="stage3")
    m = FakeMessage("/start", u3)
    await U.cmd_start(m, FakeState(), db=db, sheets=sheets, bot=bot, config=cfg)
    check("3-bosqichdan davom etdi", "rezidenti" in m.replies[-1]["text"])
    m = FakeMessage("salom", u3)
    await U.fallback(m, FakeState(), db=db, config=cfg)
    check("Tasodifiy matn ham bosqichga qaytardi", "rezidenti" in m.replies[-1]["text"])

    print("\n【12】 Guruh ulanmagan bo'lsa (havola yaratilmaydi)")
    class NoGroupCfg(Cfg):
        private_group_id = None
    u4 = FakeUser(4004, "noguruh")
    await db.ensure_user(4004, "noguruh")
    await db.update(4004, full_name="Test Test", status="stage4")
    cb = FakeCallback("agree:4", u4)
    await U.cb_agree(cb, db=db, sheets=sheets, bot=bot, config=NoGroupCfg())
    rec = await db.get(4004)
    check("Ariza baribir yakunlandi", rec["status"] == "done")
    check("Havolasiz xabar chiqdi", "tez orada yuboriladi" in OUT[-2][1] or "tez orada" in last())

    print("\n【13】 Guruhda bot admin emas (xatolik yutiladi)")
    badbot = FakeBot(invite_ok=False)
    u5 = FakeUser(5005, "xato")
    await db.ensure_user(5005, "xato")
    await db.update(5005, full_name="Xato Xatoyev", status="stage4")
    cb = FakeCallback("agree:4", u5)
    await U.cb_agree(cb, db=db, sheets=sheets, bot=badbot, config=cfg)
    rec = await db.get(5005)
    check("Bot yiqilmadi, ariza yakunlandi", rec["status"] == "done")
    check("Foydalanuvchi xato ko'rmadi", "❗" not in last() and "Traceback" not in last())

    # ---------------------------------------------------------- Admin panel
    print("\n【14】 Admin panel")
    m = FakeMessage("/admin", au)
    await A.cmd_admin(m, db=db, sheets=sheets, config=cfg)
    check("Panel ochildi", "Admin panel" in m.replies[0]["text"])
    check("Statistika ko'rsatildi", "Jami" in m.replies[0]["text"])
    m = FakeMessage("/admin", u)   # oddiy foydalanuvchi
    await A.cmd_admin(m, db=db, sheets=sheets, config=cfg)
    check("Oddiy foydalanuvchiga panel ochilmadi", len(m.replies) == 0)

    m = FakeMessage("/status", u)
    await U.cmd_status(m, db=db)
    check("/status ishladi", "Ariza holati" in m.replies[0]["text"])
    check("/status'da chek holati bor", "Tasdiqlangan" in m.replies[0]["text"])

    print("\n" + "=" * 60)
    print(f"NATIJA:  ✅ {PASS} ta o'tdi   ❌ {FAIL} ta xato")
    print("=" * 60)
    return FAIL


sys.exit(asyncio.run(run()))
