"""Muddatli bir martalik havolalar va guruhni avtomatik aniqlash."""
import asyncio, datetime as dt, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.db import Database
from bot.handlers import group as G
from bot.handlers import user as U
from tests.fakes import (OUT, FakeBot, FakeCallback, FakeChatMemberUpdated,
                         FakeMessage, FakeSheets, FakeState, FakeUser)

PASS = FAIL = 0
ADMIN_ID, GROUP_ID = 986277961, -1001234567890

def check(label, cond, extra=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}" + (f"  {extra}" if extra else ""))
    else:    FAIL += 1; print(f"  ❌ {label}  {extra}")

class Cfg:
    admin_ids = [ADMIN_ID]; admin_group_id = None; private_group_id = None
    receipt_archive_id = None
    irshod_url = "https://irshod.uz"; invite_expire_days = 7
    def is_admin(self, uid): return uid in self.admin_ids

async def main():
    db = Database(tempfile.mktemp(suffix=".db")); await db.init()
    sheets, bot, cfg = FakeSheets(), FakeBot(), Cfg()

    print("\n【1】 Guruh ulanmagan holat")
    check("resolve_group_id = None", (await G.resolve_group_id(db, cfg)) is None)

    print("\n【2】 Bot guruhga oddiy a'zo sifatida qo'shildi")
    ev = FakeChatMemberUpdated(GROUP_ID, "Startup Garage", status="member")
    await G.on_bot_status_changed(ev, db=db, bot=bot, config=cfg)
    check("adminga ogohlantirish ketdi",
          any("qo‘shildi" in x[1] and "qiling" in x[1] for x in bot.sent))
    check("guruh hali saqlanmadi", (await G.resolve_group_id(db, cfg)) is None)

    print("\n【3】 Admin qilindi, lekin havola huquqi yo'q")
    bot.sent.clear()
    ev = FakeChatMemberUpdated(GROUP_ID, "Startup Garage", status="administrator", can_invite=False)
    await G.on_bot_status_changed(ev, db=db, bot=bot, config=cfg)
    check("huquq yetishmasligi haqida xabar", any("huquq" in x[1] for x in bot.sent))
    check("guruh saqlanmadi", (await G.resolve_group_id(db, cfg)) is None)

    print("\n【4】 To'liq huquq bilan admin qilindi → avtomatik ulanish")
    bot.sent.clear()
    ev = FakeChatMemberUpdated(GROUP_ID, "Startup Garage", status="administrator", can_invite=True)
    await G.on_bot_status_changed(ev, db=db, bot=bot, config=cfg)
    check("guruh avtomatik saqlandi", (await G.resolve_group_id(db, cfg)) == GROUP_ID,
          f"-> {await G.resolve_group_id(db, cfg)}")
    check("adminga tasdiq xabari", any("Yopiq guruh ulandi" in x[1] for x in bot.sent))
    check("xabarda guruh nomi bor", any("Startup Garage" in x[1] for x in bot.sent))

    print("\n【5】 Havola yaratish — bir martalik va muddatli")
    u = FakeUser(1001, "aliuz")
    await db.ensure_user(1001, "aliuz")
    await db.update(1001, full_name="Ali Valiyev", status="stage4")
    cb = FakeCallback("agree:4", u)
    await U.cb_agree(cb, db=db, sheets=sheets, bot=bot, config=cfg)
    call = bot.invite_calls[-1]
    check("to'g'ri guruhga yaratildi", call["chat_id"] == GROUP_ID)
    check("member_limit = 1 (bir martalik)", call["member_limit"] == 1, f"-> {call['member_limit']}")
    check("expire_date berilgan", call["expire_date"] is not None)
    delta = call["expire_date"] - dt.datetime.now()
    check("muddat ≈ 7 kun", 6.9 < delta.total_seconds()/86400 < 7.1,
          f"-> {delta.total_seconds()/86400:.2f} kun")
    rec = await db.get(1001)
    check("havola DB'ga yozildi", rec["invite_link"].startswith("https://t.me/+"))
    check("tugash sanasi yozildi", bool(rec["invite_expires"]), f"-> {rec['invite_expires']}")
    check("foydalanuvchiga muddat aytildi", any("7 kun" in x for _, x in OUT[-4:]))

    print("\n【6】 Amaldagi havola — /start qayta yaratmaydi")
    before = len(bot.invites)
    m = FakeMessage("/start", u)
    await U.cmd_start(m, FakeState(), db=db, sheets=sheets, bot=bot, config=cfg)
    check("yangi havola yaratilmadi", len(bot.invites) == before, f"-> {len(bot.invites)}")
    check("eski havola qaytarildi", "allaqachon" in m.replies[0]["text"])

    print("\n【7】 Muddati tugagan havola → avtomatik yangilanadi")
    await db.update(1001, invite_expires="2020-01-01 00:00:00")
    rec = await db.get(1001)
    check("link_alive() False qaytardi", U.link_alive(rec) is False)
    m = FakeMessage("/start", u)
    await U.cmd_start(m, FakeState(), db=db, sheets=sheets, bot=bot, config=cfg)
    check("yangi havola yaratildi", len(bot.invites) == before + 1)
    check("«havola yangilandi» xabari", "yangilandi" in m.replies[0]["text"])
    rec = await db.get(1001)
    check("yangi muddat kelajakda",
          dt.datetime.strptime(rec["invite_expires"], "%Y-%m-%d %H:%M:%S") > dt.datetime.now())
    check("Sheets yangilandi", sheets.rows[1001]["invite_link"] == rec["invite_link"])

    print("\n【8】 Muddat sozlanishi (30 kun)")
    class Cfg30(Cfg): invite_expire_days = 30
    await db.ensure_user(2002, "bek"); await db.update(2002, status="stage4")
    cb = FakeCallback("agree:4", FakeUser(2002, "bek"))
    await U.cb_agree(cb, db=db, sheets=sheets, bot=bot, config=Cfg30())
    d = (bot.invite_calls[-1]["expire_date"] - dt.datetime.now()).total_seconds()/86400
    check("muddat ≈ 30 kun", 29.9 < d < 30.1, f"-> {d:.2f} kun")
    check("matnda 30 kun yozilgan", any("30 kun" in x for _, x in OUT[-4:]))

    print("\n【9】 Bot guruhdan chiqarildi")
    bot.sent.clear()
    ev = FakeChatMemberUpdated(GROUP_ID, "Startup Garage", status="kicked")
    await G.on_bot_status_changed(ev, db=db, bot=bot, config=cfg)
    check("guruh o'chirildi", (await G.resolve_group_id(db, cfg)) is None)
    check("adminga xabar berildi", any("chiqarildi" in x[1] for x in bot.sent))

    print("\n【10】 .env dagi guruh avtomatik topilganidan ustun")
    class CfgEnv(Cfg): private_group_id = -100999
    await db.set_setting("private_group_id", str(GROUP_ID))
    check(".env ustunlik qildi", (await G.resolve_group_id(db, CfgEnv())) == -100999)
    check("bo'sh .env'da baza ishlatildi", (await G.resolve_group_id(db, cfg)) == GROUP_ID)

    print("\n" + "="*60)
    print(f"NATIJA:  ✅ {PASS} ta o'tdi   ❌ {FAIL} ta xato")
    print("="*60)
    return FAIL

sys.exit(asyncio.run(main()))
