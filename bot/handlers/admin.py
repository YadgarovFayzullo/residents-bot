"""Admin: chek tekshiruvi, statistika, sinxronlash, e'lon."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import archive
from .. import keyboards as kb
from .. import sync
from .. import texts as t
from ..db import ST_RECEIPT_SENT, ST_RECEIPT_WAIT, ST_STAGE2, STATUS_LABELS, now
from ..states import AdminForm

log = logging.getLogger(__name__)
router = Router(name="admin")


def _is_admin(user_id: int, config) -> bool:
    return config.is_admin(user_id)


# ---------------------------------------------------------------- /myid
@router.message(Command("myid"))
async def cmd_myid(message: Message, **_):
    await message.answer(
        f"🆔 Sizning ID: <code>{message.from_user.id}</code>\n"
        f"💬 Chat ID: <code>{message.chat.id}</code>\n\n"
        "<i>Bu ID ni .env faylidagi ADMIN_IDS ga qo‘shing.</i>"
    )


# ---------------------------------------------------------------- /admin
@router.message(Command("admin"))
async def cmd_admin(message: Message, db, sheets, config, **_):
    if not _is_admin(message.from_user.id, config):
        return
    st = await db.stats()
    ok, info = await sheets.check()
    await message.answer(
        "🛠 <b>Admin panel</b>\n\n"
        f"👥 Jami: <b>{st.get('total', 0)}</b>\n"
        f"⏳ Tekshiruvda: <b>{st.get('pending', 0)}</b>\n"
        f"✅ Yakunlangan: <b>{st.get('done', 0)}</b>\n\n"
        f"📊 Sheets [{sheets.mode}]: {'🟢 ' + info if ok else '🔴 ' + info}\n"
        f"📥 Sinxronlanmagan: <b>{len(await db.unsynced())}</b> ta",
        reply_markup=kb.admin_kb(),
    )


@router.callback_query(F.data == "adm:stats")
async def cb_stats(cb: CallbackQuery, db, config, **_):
    if not _is_admin(cb.from_user.id, config):
        await cb.answer("Ruxsat yo‘q", show_alert=True)
        return
    await cb.answer()
    st = await db.stats()
    lines = [f"• {STATUS_LABELS.get(k, k)}: <b>{v}</b>" for k, v in st.items()
             if k not in ("total", "pending")]
    await cb.message.answer(
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchi: <b>{st.get('total', 0)}</b>\n"
        f"⏳ Chek tekshiruvda: <b>{st.get('pending', 0)}</b>\n\n"
        "<b>Bosqichlar bo‘yicha:</b>\n" + "\n".join(lines)
    )


@router.callback_query(F.data == "adm:pending")
async def cb_pending(cb: CallbackQuery, db, bot, config, **_):
    if not _is_admin(cb.from_user.id, config):
        await cb.answer("Ruxsat yo‘q", show_alert=True)
        return
    await cb.answer()
    rows = await db.list_by_status(ST_RECEIPT_SENT)
    if not rows:
        await cb.message.answer("✅ Tekshirilmagan cheklar yo‘q.")
        return
    await cb.message.answer(f"⏳ <b>{len(rows)} ta chek tekshiruvda:</b>")
    for u in rows[:20]:
        caption = _receipt_info(u)
        markup = kb.review_kb(u["user_id"])
        try:
            if u.get("receipt_type") == "photo":
                await bot.send_photo(cb.from_user.id, u["receipt_file_id"],
                                     caption=caption, reply_markup=markup)
            elif u.get("receipt_file_id"):
                await bot.send_document(cb.from_user.id, u["receipt_file_id"],
                                        caption=caption, reply_markup=markup)
            else:
                await bot.send_message(cb.from_user.id, caption, reply_markup=markup)
        except Exception as e:
            log.warning("pending yuborishda xato: %s", e)


@router.callback_query(F.data == "adm:sync")
async def cb_sync(cb: CallbackQuery, db, sheets, config, **_):
    if not _is_admin(cb.from_user.id, config):
        await cb.answer("Ruxsat yo‘q", show_alert=True)
        return
    await cb.answer("Sinxronlash boshlandi…")
    await _do_sync(cb.message, db, sheets)


@router.message(Command("sync"))
async def cmd_sync(message: Message, db, sheets, config, **_):
    if not _is_admin(message.from_user.id, config):
        return
    await _do_sync(message, db, sheets)


async def _do_sync(message: Message, db, sheets):
    if not sheets.enabled:
        await message.answer(
            "🔴 <b>Google Sheets ulanmagan</b>\n\n"
            "Ikkita usuldan birini tanlang:\n\n"
            "<b>1. Apps Script</b> (oddiyroq)\n"
            "Jadval → Kengaytmalar → Apps Script → skriptni joylang → "
            "Deploy → Web app. Chiqqan URL ni <code>SHEET_WEBHOOK_URL</code> ga yozing.\n\n"
            "<b>2. Service account</b>\n"
            "<code>credentials.json</code> faylini loyihaga joylang.\n\n"
            "ℹ️ Hozircha barcha ma’lumotlar bazada saqlanmoqda — yo‘qolmaydi. "
            "Ulaganingizdan so‘ng /sync ularni jadvalga ko‘chiradi."
        )
        return
    rows = await db.unsynced()
    if not rows:
        await message.answer("✅ Barcha yozuvlar allaqachon sinxronlangan.")
        return
    status = await message.answer(f"🔄 {len(rows)} ta yozuv sinxronlanmoqda…")
    ok = 0
    for u in rows:
        row = await sheets.upsert(u)
        if row:
            await db.mark_synced(u["user_id"], row)
            ok += 1
    text = f"✅ Sinxronlandi: <b>{ok}</b> / {len(rows)}"
    if ok < len(rows):
        text += f"\n\n🔴 Xato: {sheets.last_error}"
    try:
        await status.edit_text(text)
    except Exception:
        await message.answer(text)


# ---------------------------------------------------------------- Chek arxivi
def _receipt_info(u: dict) -> str:
    label = {
        "none": "Yuborilmagan", "pending": "⏳ Tekshiruvda",
        "approved": "✅ Tasdiqlangan", "rejected": "❌ Rad etilgan",
    }.get(u.get("receipt_status") or "none", "—")
    lines = [
        f"👤 <b>{u.get('full_name') or '—'}</b>",
        f"📞 {u.get('phone') or '—'}",
        f"💬 {u.get('username') or '—'}",
        f"🆔 <code>{u['user_id']}</code>",
        f"🧾 Chek: {label}",
    ]
    if u.get("receipt_at"):
        lines.append(f"🕒 {u['receipt_at']}")
    if u.get("reject_reason"):
        lines.append(f"✍️ Sabab: {u['reject_reason']}")
    if u.get("receipt_link"):
        lines.append(f'🔗 <a href="{u["receipt_link"]}">Arxivdagi chek</a>')
    return "\n".join(lines)


@router.message(Command("chek"))
async def cmd_chek(message: Message, db, bot, config, **_):
    """/chek <ID | ism | telefon | @username> — chekni qayta ko'rish."""
    if not _is_admin(message.from_user.id, config):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "🔎 <b>Chekni topish</b>\n\n"
            "<code>/chek 123456789</code> — Telegram ID bo‘yicha\n"
            "<code>/chek Ali Valiyev</code> — ism bo‘yicha\n"
            "<code>/chek 9012345</code> — telefon bo‘yicha\n"
            "<code>/chek @username</code>"
        )
        return

    rows = await db.search(parts[1])
    if not rows:
        await message.answer("❌ Hech narsa topilmadi.")
        return
    if len(rows) > 5:
        await message.answer(f"🔎 {len(rows)} ta natija — birinchi 5 tasi:")
        rows = rows[:5]

    for u in rows:
        info = _receipt_info(u)
        if not u.get("receipt_file_id"):
            await message.answer(info + "\n\n<i>Chek yuborilmagan.</i>")
            continue
        try:
            await archive.send_receipt(
                bot, message.chat.id, u["receipt_file_id"],
                u.get("receipt_type") or "photo", info,
                kb.review_kb(u["user_id"]) if u.get("receipt_status") == "pending" else None,
            )
        except Exception as e:
            log.warning("chek yuborilmadi (%s): %s", u["user_id"], e)
            await message.answer(info + f"\n\n⚠️ Faylni ochib bo‘lmadi: {e}")


@router.message(Command("arxiv"))
async def cmd_arxiv(message: Message, bot, config, **_):
    """Chek arxivi sozlanganini tekshirish."""
    if not _is_admin(message.from_user.id, config):
        return
    chat_id = config.receipt_archive_id or config.admin_group_id
    if not chat_id:
        await message.answer(
            "🔴 <b>Chek arxivi sozlanmagan</b>\n\n"
            "Yopiq kanal oching → botni admin qiling → bot sizga kanal ID sini "
            "yuboradi → uni <code>.env</code> dagi <code>RECEIPT_ARCHIVE_ID</code> ga "
            "yozing va botni qayta ishga tushiring."
        )
        return
    try:
        chat = await bot.get_chat(chat_id)
        me = await bot.get_chat_member(chat_id, (await bot.get_me()).id)
        await message.answer(
            "🟢 <b>Chek arxivi</b>\n\n"
            f"📛 {chat.title}\n"
            f"🆔 <code>{chat_id}</code>\n"
            f"👤 Bot holati: {me.status}\n"
            f"🔗 Havola ko‘rinishi: <code>{archive.message_link(chat_id, 1)}</code>\n\n"
            + ("" if config.receipt_archive_id else
               "<i>Alohida kanal ko‘rsatilmagan — admin guruhi arxiv sifatida ishlatilmoqda.</i>")
        )
    except Exception as e:
        await message.answer(
            f"🔴 Arxivga ulanib bo‘lmadi: <code>{e}</code>\n\n"
            f"Saqlangan ID: <code>{chat_id}</code>"
        )


@router.message(Command("resync"))
async def cmd_resync(message: Message, db, sheets, config, **_):
    """Jadvaldagi barcha qatorlarni qaytadan yozadi (ustunlar o'zgarganda)."""
    if not _is_admin(message.from_user.id, config):
        return
    n = await db.mark_all_unsynced()
    await message.answer(f"🔄 {n} ta yozuv qayta sinxronlashga belgilandi.")
    await _do_sync(message, db, sheets)


# ---------------------------------------------------------------- Chek tekshiruvi
@router.callback_query(F.data.startswith("ok:"))
async def cb_approve(cb: CallbackQuery, db, sheets, bot, config, **_):
    if not _is_admin(cb.from_user.id, config):
        await cb.answer("Ruxsat yo‘q", show_alert=True)
        return
    user_id = int(cb.data.split(":")[1])
    user = await db.get(user_id)
    if not user:
        await cb.answer("Foydalanuvchi topilmadi", show_alert=True)
        return
    if user.get("receipt_status") == "approved":
        await cb.answer("Bu chek allaqachon tasdiqlangan.", show_alert=True)
        return

    await cb.answer("Tasdiqlandi ✅")
    user = await db.update(
        user_id,
        receipt_status="approved",
        reviewed_by=cb.from_user.id,
        reviewed_at=now(),
        reject_reason="",
        status=ST_STAGE2,
    )
    await sync.push_now(db, sheets, user)
    await _mark_caption(cb, f"✅ TASDIQLANDI — @{cb.from_user.username or cb.from_user.id}")

    try:
        await bot.send_message(user_id, t.RECEIPT_APPROVED)
        await bot.send_message(user_id, t.STAGE_2, reply_markup=kb.agree_kb(2))
    except Exception as e:
        log.error("Foydalanuvchiga (%s) xabar yuborilmadi: %s", user_id, e)
        await cb.message.answer(f"⚠️ Foydalanuvchiga xabar yetmadi: {e}")


@router.callback_query(F.data.startswith("no:"))
async def cb_reject(cb: CallbackQuery, state: FSMContext, config, **_):
    if not _is_admin(cb.from_user.id, config):
        await cb.answer("Ruxsat yo‘q", show_alert=True)
        return
    user_id = int(cb.data.split(":")[1])
    await cb.answer()
    await state.set_state(AdminForm.reject_reason)
    await state.update_data(reject_user_id=user_id, src_chat=cb.message.chat.id,
                            src_msg=cb.message.message_id)
    await cb.message.answer(
        f"✍️ <code>{user_id}</code> uchun rad etish sababini yozing.\n\n"
        "Sababsiz rad etish uchun <b>-</b> yuboring.\n"
        "Bekor qilish uchun /cancel."
    )


@router.message(AdminForm.reject_reason, Command("cancel"))
async def cancel_reject(message: Message, state: FSMContext, **_):
    await state.clear()
    await message.answer("❎ Bekor qilindi.")


@router.message(AdminForm.reject_reason, F.text)
async def got_reject_reason(message: Message, state: FSMContext, db, sheets, bot, config, **_):
    data = await state.get_data()
    user_id = data.get("reject_user_id")
    await state.clear()
    reason = message.text.strip()
    if reason == "-":
        reason = ""

    user = await db.update(
        user_id,
        receipt_status="rejected",
        reviewed_by=message.from_user.id,
        reviewed_at=now(),
        reject_reason=reason,
        status=ST_RECEIPT_WAIT,
    )
    await sync.push_now(db, sheets, user)
    await message.answer(f"❌ <code>{user_id}</code> uchun chek rad etildi.")

    try:
        await bot.send_message(
            user_id,
            t.receipt_rejected(reason),
            reply_markup=kb.receipt_kb(config.irshod_url),
        )
    except Exception as e:
        log.error("Rad etish xabari yetmadi (%s): %s", user_id, e)
        await message.answer(f"⚠️ Foydalanuvchiga xabar yetmadi: {e}")


async def _mark_caption(cb: CallbackQuery, mark: str) -> None:
    """Admin xabaridagi tugmalarni olib, natijani caption'ga qo'shadi."""
    try:
        base = cb.message.caption or cb.message.text or ""
        new = f"{base}\n\n<b>{mark}</b>"
        if cb.message.caption is not None:
            await cb.message.edit_caption(caption=new, reply_markup=None)
        else:
            await cb.message.edit_text(new, reply_markup=None)
    except Exception:
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass


# ---------------------------------------------------------------- E'lon
@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext, config, **_):
    if not _is_admin(message.from_user.id, config):
        return
    await state.set_state(AdminForm.broadcast)
    await message.answer(
        "📣 E’lon matnini yuboring (rasm ham bo‘lishi mumkin).\n\nBekor qilish: /cancel"
    )


@router.message(AdminForm.broadcast, Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext, **_):
    await state.clear()
    await message.answer("❎ Bekor qilindi.")


@router.message(AdminForm.broadcast)
async def do_broadcast(message: Message, state: FSMContext, db, bot, **_):
    await state.clear()
    users = await db.all_users()
    sent = failed = 0
    status = await message.answer(f"📣 {len(users)} ta foydalanuvchiga yuborilmoqda…")
    for u in users:
        try:
            await message.send_copy(chat_id=u["user_id"])
            sent += 1
        except Exception:
            failed += 1
    await status.edit_text(f"📣 <b>E’lon yakunlandi</b>\n\n✅ Yetdi: {sent}\n❌ Yetmadi: {failed}")
