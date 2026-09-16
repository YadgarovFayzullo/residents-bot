"""Admin guruhidagi kartochkalar aralashib ketmasligini tekshiradi.

Stsenariy: bir odam faqat ro'yxatdan o'tdi, uchtasi to'liq o'tdi,
yana bittasi keyinroq to'liq o'tdi. Har kimda bitta kartochka bo'lib
qolishi va u o'z holatini ko'rsatishi shart.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import card, sync                                   # noqa: E402
from bot.db import Database                                  # noqa: E402
from bot.handlers import admin as A                          # noqa: E402
from bot.handlers import user as U                           # noqa: E402
from fakes import (FakeBot, FakeCallback, FakeMessage, FakePhoto,  # noqa: E402
                   FakeSheets, FakeState, FakeUser)

ADMIN_GROUP = -5562057451
ADMIN_ID = 7001

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


async def settle():
    await sync.drain()
    await card.drain()


async def register(uid, name, phone, D):
    """1-bosqich: anketa to'ldirish."""
    me = FakeUser(uid, f"user{uid}")
    st = FakeState()
    await D["db"].ensure_user(uid, f"user{uid}")
    await U.cb_start_form(FakeCallback("start_form", user=me), st,
                          db=D["db"], sheets=D["sheets"])
    await U.got_full_name(FakeMessage(user=me, text=name), st,
                          db=D["db"], sheets=D["sheets"])
    await U.got_phone_text(FakeMessage(user=me, text=phone), st,
                           db=D["db"], sheets=D["sheets"])
    await U.got_username_text(FakeMessage(user=me, text=f"@user{uid}"), st, **D)
    await settle()
    return me, st


async def full_pass(me, st, D):
    """2–5-bosqichlar: chek, tasdiq va uchta rozilik."""
    st.state = U.Form.receipt
    await U.got_receipt(FakeMessage(user=me, photo=[FakePhoto(f"F{me.id}")]), st, **D)
    await settle()
    await A.cb_approve(FakeCallback(f"ok:{me.id}", user=FakeUser(ADMIN_ID)), **D)
    await settle()
    for stage in (2, 3, 4):
        await U.cb_agree(FakeCallback(f"agree:{stage}", user=me), **D)
        await settle()


MARK = "📋 <b>Ariza</b>"        # chek xabaridan ajratish uchun


def is_card(text, uid=None):
    if not text.startswith(MARK):
        return False
    return uid is None or f"<code>{uid}</code>" in text


def cards_for(bot, uid):
    """Shu foydalanuvchi uchun guruhga ketgan yangi kartochkalar."""
    return [t for c, t in bot.sent if c == ADMIN_GROUP and is_card(t, uid)]


def edits_for(bot, uid):
    return [(m, t) for c, m, t in bot.edits if c == ADMIN_GROUP and is_card(t, uid)]


async def run():
    db = Database(tempfile.mktemp(suffix=".db"))
    await db.init()
    bot, sheets, cfg = FakeBot(), FakeSheets(), Cfg()
    D = dict(db=db, sheets=sheets, bot=bot, config=cfg)

    print("\n【1】 Faqat ro'yxatdan o'tgan odam")
    a, _ = await register(101, "Aziz Azizov", "+998901110001", D)
    check("kartochka yuborildi", len(cards_for(bot, 101)) == 1,
          f"-> {len(cards_for(bot, 101))} ta")
    text = cards_for(bot, 101)[0]
    check("1-bosqich belgilandi", "1️⃣ Ro‘yxatdan o‘tish — ✅" in text)
    check("chek hali yuborilmagan", "2️⃣ Chek (Playbook) — ⏸" in text)

    print("\n【2】 Uch kishi to'liq o'tdi")
    done = []
    for uid, name in ((102, "Bek Bekov"), (103, "Dilshod Dilshodov"), (104, "Eldor Eldorov")):
        me, st = await register(uid, name, f"+99890111{uid}", D)
        await full_pass(me, st, D)
        done.append(uid)
    for uid in done:
        check(f"{uid}: bitta kartochka", len(cards_for(bot, uid)) == 1,
              f"-> {len(cards_for(bot, uid))} ta")

    print("\n【3】 Yana bittasi keyinroq to'liq o'tdi")
    e, est = await register(105, "Farrux Farruxov", "+998901110005", D)
    await full_pass(e, est, D)
    check("105: bitta kartochka", len(cards_for(bot, 105)) == 1)

    print("\n【4】 Aralashib ketmadi — har kimda bitta xabar")
    all_cards = [t for c, t in bot.sent if c == ADMIN_GROUP and is_card(t)]
    check("jami 5 ta kartochka", len(all_cards) == 5, f"-> {len(all_cards)} ta")
    ids = {101, 102, 103, 104, 105}
    check("har bir foydalanuvchiga bittadan",
          all(len(cards_for(bot, u)) == 1 for u in ids))

    print("\n【5】 Keyingi bosqichlar o'sha xabarni tahrirlaydi")
    msg_ids = {u: {m for m, _ in edits_for(bot, u)} for u in ids}
    check("102 uchun bitta message_id", len(msg_ids[102]) == 1, f"-> {msg_ids[102]}")
    check("101 tahrirlanmadi (bosqich o'zgarmagan)", not edits_for(bot, 101))
    check("turli odamlarning id'lari har xil",
          len({next(iter(msg_ids[u])) for u in (102, 103, 104, 105)}) == 4)

    print("\n【6】 Oxirgi holat to'g'ri ko'rinadi")
    last_101 = cards_for(bot, 101)[-1]
    last_102 = edits_for(bot, 102)[-1][1]
    check("101 — chek kutilmoqda", "Chek kutilmoqda" in last_101, f"-> {last_101[-60:]}")
    check("102 — yakunlandi", "Yakunlandi" in last_102)
    check("102 — barcha roziliklar ✅", last_102.count("— ✅") >= 4,
          f"-> {last_102.count('— ✅')} ta")

    print("\n【7】 Bazada message_id saqlandi")
    rec = await db.get(102)
    check("admin_msg_id yozildi", bool(rec["admin_msg_id"]), f"-> {rec['admin_msg_id']}")

    print("\n【8】 ADMIN_GROUP_ID bo'sh bo'lsa — yuborilmaydi")
    class NoGroup(Cfg):
        admin_group_id = None
    before = len(bot.sent)
    card.refresh(bot, db, NoGroup(), await db.get(101))
    await card.drain()
    check("hech narsa yuborilmadi", len(bot.sent) == before)

    print("\n" + "=" * 60)
    print(f"NATIJA:  ✅ {PASS} ta o'tdi   ❌ {FAIL} ta xato")
    print("=" * 60)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
