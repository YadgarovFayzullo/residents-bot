"""Foydalanuvchi oqimi: /start → anketa → chek → 2/3/4-bosqich → yakun."""
from __future__ import annotations

import datetime as dt
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from .. import archive
from .. import card
from .. import keyboards as kb
from .. import sync
from .. import texts as t
from ..db import (
    ST_DECLINED,
    ST_DONE,
    ST_FORM,
    ST_NEW,
    ST_RECEIPT_SENT,
    ST_RECEIPT_WAIT,
    ST_STAGE2,
    ST_STAGE3,
    ST_STAGE4,
    now,
)
from ..states import Form
from ..validators import clean_full_name, clean_phone, clean_username
from .group import resolve_group_id

log = logging.getLogger(__name__)
router = Router(name="user")

STAGE_TEXT = {2: t.STAGE_2, 3: t.STAGE_3, 4: t.STAGE_4}
STAGE_STATUS = {2: ST_STAGE2, 3: ST_STAGE3, 4: ST_STAGE4}


# ---------------------------------------------------------------- yordamchi
async def show_stage(message: Message, stage: int) -> None:
    await message.answer(STAGE_TEXT[stage], reply_markup=kb.agree_kb(stage))


async def make_invite_link(user_id: int, db, bot, config) -> tuple[str | None, str]:
    """Bir martalik, muddatli taklif havolasi yaratadi.

    Qaytaradi: (havola, tugash_sanasi)
    """
    group_id = await resolve_group_id(db, config)
    if not group_id:
        return None, ""

    expires_at = dt.datetime.now() + dt.timedelta(days=config.invite_expire_days)
    try:
        invite = await bot.create_chat_invite_link(
            chat_id=group_id,
            name=f"user_{user_id}"[:32],
            member_limit=1,                       # faqat bitta odam kira oladi
            expire_date=expires_at,               # muddati tugagach ishlamaydi
        )
        return invite.invite_link, expires_at.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        log.error("Taklif havolasini yaratib bo'lmadi (%s): %s", user_id, e)
        return None, ""


def link_alive(user: dict) -> bool:
    """Havola hali amal qiladimi?"""
    if not user.get("invite_link"):
        return False
    raw = user.get("invite_expires")
    if not raw:
        return True
    try:
        return dt.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S") > dt.datetime.now()
    except ValueError:
        return True


async def finish_application(message: Message, user_id: int, db, sheets, bot, config):
    """Yakuniy bosqich: bir martalik havola yaratib, arizani yopadi."""
    link, expires = await make_invite_link(user_id, db, bot, config)

    user = await db.update(
        user_id,
        status=ST_DONE,
        invite_link=link or "",
        invite_expires=expires,
        finished_at=now(),
    )
    await sync.push_now(db, sheets, user)
    card.refresh(bot, db, config, user)

    if link:
        await message.answer(
            t.finished(config.invite_expire_days), reply_markup=kb.invite_kb(link)
        )
    else:
        await message.answer(t.FINISHED_NO_LINK)

    # Adminlarga xabar
    text = (
        "🎉 <b>Yangi rezident — ariza yakunlandi</b>\n\n"
        f"👤 {user.get('full_name')}\n"
        f"📞 {user.get('phone')}\n"
        f"💬 {user.get('username')}\n"
        f"🆔 <code>{user_id}</code>"
    )
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass


# ---------------------------------------------------------------- /start
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db, sheets, bot, config, **_):
    await state.clear()
    u = message.from_user
    user = await db.ensure_user(u.id, u.username)
    status = user.get("status")
    sync.push(db, sheets, user)

    # Yakunlanganlar — havolani qayta ko'rsatamiz
    if status == ST_DONE:
        if link_alive(user):
            await message.answer(
                t.ALREADY_DONE, reply_markup=kb.invite_kb(user["invite_link"])
            )
            return
        # Havola muddati tugagan yoki umuman yaratilmagan — yangisini beramiz
        link, expires = await make_invite_link(u.id, db, bot, config)
        if link:
            user = await db.update(u.id, invite_link=link, invite_expires=expires)
            await sync.push_now(db, sheets, user)
            await message.answer(
                t.link_renewed(config.invite_expire_days), reply_markup=kb.invite_kb(link)
            )
        else:
            await message.answer(t.FINISHED_NO_LINK)
        return

    # Chek tekshiruvda
    if status == ST_RECEIPT_SENT:
        await message.answer(t.WAIT_ADMIN)
        return

    # 2/3/4-bosqichda to'xtab qolgan bo'lsa — o'sha joydan davom etadi
    if status in (ST_STAGE2, ST_STAGE3, ST_STAGE4):
        stage = {ST_STAGE2: 2, ST_STAGE3: 3, ST_STAGE4: 4}[status]
        await message.answer(t.RECEIPT_APPROVED)
        await show_stage(message, stage)
        return

    # Chek kutilmoqda
    if status == ST_RECEIPT_WAIT and user.get("full_name"):
        await message.answer(t.PROJECT_SELECT, reply_markup=kb.receipt_kb(config.irshod_url))
        return

    await message.answer(t.WELCOME, reply_markup=kb.start_kb())


@router.callback_query(F.data == "start_form")
async def cb_start_form(cb: CallbackQuery, state: FSMContext, db, sheets, **_):
    await cb.answer()
    await db.reset(cb.from_user.id)
    user = await db.update(cb.from_user.id, status=ST_FORM)
    sync.push(db, sheets, user)
    await state.set_state(Form.full_name)
    await cb.message.answer(t.ASK_FULL_NAME, reply_markup=kb.REMOVE)


# ---------------------------------------------------------------- 1. Ism
@router.message(Form.full_name, F.text)
async def got_full_name(message: Message, state: FSMContext, db, sheets, **_):
    name = clean_full_name(message.text)
    if not name:
        await message.answer(t.ERR_FULL_NAME)
        return
    user = await db.update(message.from_user.id, full_name=name)
    sync.push(db, sheets, user)
    await state.set_state(Form.phone)
    await message.answer(t.ASK_PHONE, reply_markup=kb.phone_kb())


@router.message(Form.full_name)
async def bad_full_name(message: Message, **_):
    await message.answer(t.ERR_FULL_NAME)


# ---------------------------------------------------------------- 2. Telefon
@router.message(Form.phone, F.contact)
async def got_contact(message: Message, state: FSMContext, db, sheets, **_):
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer(
            "❗️ Iltimos, <b>o‘zingizning</b> raqamingizni yuboring.",
            reply_markup=kb.phone_kb(),
        )
        return
    phone = clean_phone(message.contact.phone_number) or message.contact.phone_number
    await _save_phone(message, state, db, sheets, phone)


@router.message(Form.phone, F.text)
async def got_phone_text(message: Message, state: FSMContext, db, sheets, **_):
    phone = clean_phone(message.text)
    if not phone:
        await message.answer(t.ERR_PHONE, reply_markup=kb.phone_kb())
        return
    await _save_phone(message, state, db, sheets, phone)


async def _save_phone(message: Message, state: FSMContext, db, sheets, phone: str):
    user = await db.update(message.from_user.id, phone=phone)
    sync.push(db, sheets, user)
    await state.set_state(Form.username)
    await message.answer("✅ Raqam saqlandi.", reply_markup=kb.REMOVE)
    await message.answer(
        t.ASK_USERNAME, reply_markup=kb.username_kb(message.from_user.username)
    )


@router.message(Form.phone)
async def bad_phone(message: Message, **_):
    await message.answer(t.ERR_PHONE, reply_markup=kb.phone_kb())


# ---------------------------------------------------------------- 3. Username
@router.message(Form.username, F.text)
async def got_username_text(message: Message, state: FSMContext, db, sheets, bot, config, **_):
    uname = clean_username(message.text)
    if not uname:
        await message.answer(
            t.ERR_USERNAME, reply_markup=kb.username_kb(message.from_user.username)
        )
        return
    await _save_username(message, state, db, sheets, bot, config, uname)


# Holat filtri yo'q: bot qayta ishga tushsa FSM o'chadi, lekin tugma ishlashi shart.
@router.callback_query(F.data == "use_tg_username")
async def cb_use_tg_username(cb: CallbackQuery, state: FSMContext, db, sheets, bot, config, **_):
    await cb.answer()
    uname = f"@{cb.from_user.username}" if cb.from_user.username else "—"
    await _save_username(cb.message, state, db, sheets, bot, config, uname,
                         user_id=cb.from_user.id)


@router.callback_query(F.data == "no_username")
async def cb_no_username(cb: CallbackQuery, state: FSMContext, db, sheets, bot, config, **_):
    await cb.answer()
    await _save_username(cb.message, state, db, sheets, bot, config, "—",
                         user_id=cb.from_user.id)


async def _save_username(message, state, db, sheets, bot, config, uname, user_id=None):
    uid = user_id or message.from_user.id
    current = await db.get(uid)

    # Anketa ma'lumotlari yo'q — noldan boshlaymiz
    if not current or not current.get("full_name") or not current.get("phone"):
        await state.clear()
        await message.answer(t.UNKNOWN, reply_markup=kb.start_kb())
        return

    # Eskirgan tugma: foydalanuvchi allaqachon keyingi bosqichda
    if current.get("status") not in (ST_NEW, ST_FORM):
        return

    user = await db.update(uid, username=uname, status=ST_RECEIPT_WAIT)
    sync.push(db, sheets, user)
    card.refresh(bot, db, config, user)
    await state.clear()
    await message.answer(t.summary(user))
    await message.answer(t.PROJECT_SELECT, reply_markup=kb.receipt_kb(config.irshod_url))


@router.message(Form.username)
async def bad_username(message: Message, **_):
    await message.answer(
        t.ERR_USERNAME, reply_markup=kb.username_kb(message.from_user.username)
    )


# ---------------------------------------------------------------- 4. Chek
@router.callback_query(F.data == "send_receipt")
async def cb_send_receipt(cb: CallbackQuery, state: FSMContext, db, **_):
    await cb.answer()
    user = await db.get(cb.from_user.id)
    if not user or not user.get("full_name"):
        await cb.message.answer(t.WELCOME, reply_markup=kb.start_kb())
        return
    await state.set_state(Form.receipt)
    await cb.message.answer(t.ASK_RECEIPT, reply_markup=kb.REMOVE)


@router.message(Form.receipt, F.photo | F.document)
async def got_receipt(message: Message, state: FSMContext, db, sheets, bot, config, **_):
    if message.photo:
        file_id, ftype = message.photo[-1].file_id, "photo"
    else:
        doc = message.document
        mime = (doc.mime_type or "").lower()
        if not (mime.startswith("image/") or mime == "application/pdf"):
            await message.answer(t.ERR_RECEIPT)
            return
        file_id, ftype = doc.file_id, "document"

    uid = message.from_user.id
    when = now()
    user = await db.update(
        uid,
        receipt_file_id=file_id,
        receipt_type=ftype,
        receipt_status="pending",
        receipt_at=when,
        receipt_msg_id=None,
        receipt_link=None,
        reject_reason="",
        status=ST_RECEIPT_SENT,
    )
    await state.clear()
    sync.push(db, sheets, user)
    await message.answer(t.RECEIPT_RECEIVED)

    # Arxiv: alohida kanal ko'rsatilmagan bo'lsa — admin guruhi arxiv bo'ladi
    archive_chat = config.receipt_archive_id or config.admin_group_id
    archive_msg_id = None

    if config.receipt_archive_id:
        try:
            msg = await archive.send_receipt(
                bot, config.receipt_archive_id, file_id, ftype,
                archive.archive_caption(user, uid, when),
            )
            archive_msg_id = msg.message_id
        except Exception as e:
            log.error("Chek arxivga saqlanmadi (%s): %s", config.receipt_archive_id, e)

    caption = (
        "🧾 <b>Yangi chek — tekshiruv kutilmoqda</b>\n\n"
        f"👤 <b>Ism familiya:</b> {user.get('full_name')}\n"
        f"📞 <b>Telefon:</b> {user.get('phone')}\n"
        f"💬 <b>Username:</b> {user.get('username')}\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"🕒 {when}"
    )
    markup = kb.review_kb(uid)
    targets = list(config.admin_ids)
    # Admin guruhida faqat ariza kartochkalari turadi. Chek u yerga alohida
    # arxiv bo'lmagandagina boradi — aks holda guruh aralashib ketadi.
    if config.admin_group_id and not config.receipt_archive_id:
        targets.append(config.admin_group_id)

    sent = 0
    for target in targets:
        try:
            msg = await archive.send_receipt(bot, target, file_id, ftype, caption, markup)
            if archive_msg_id is None and target == archive_chat:
                archive_msg_id = msg.message_id
            sent += 1
        except Exception as e:
            log.warning("Adminga (%s) yuborilmadi: %s", target, e)
    if not sent:
        log.error("Chek hech bir adminga yetib bormadi! ADMIN_IDS ni tekshiring.")

    link = archive.message_link(archive_chat, archive_msg_id)
    if archive_msg_id:
        user = await db.update(uid, receipt_msg_id=archive_msg_id, receipt_link=link)
    else:
        log.warning("Chek arxivlanmadi (RECEIPT_ARCHIVE_ID / ADMIN_GROUP_ID bo'sh?)")
    await sync.push_now(db, sheets, user)
    card.refresh(bot, db, config, user)


@router.message(Form.receipt)
async def bad_receipt(message: Message, **_):
    await message.answer(t.ERR_RECEIPT)


# ---------------------------------------------------------------- 2/3/4-bosqich
@router.callback_query(F.data.startswith("agree:"))
async def cb_agree(cb: CallbackQuery, db, sheets, bot, config, **_):
    stage = int(cb.data.split(":")[1])
    user = await db.get(cb.from_user.id)
    if not user:
        await cb.answer()
        await cb.message.answer(t.WELCOME, reply_markup=kb.start_kb())
        return

    # Tugma eskirgan bo'lsa (allaqachon bosilgan) — takror ishlamasin
    if user.get("status") != STAGE_STATUS[stage]:
        await cb.answer("Bu bosqich allaqachon tasdiqlangan.", show_alert=True)
        return

    await cb.answer("Qabul qilindi ✅")
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    field = {2: "agree_stage2", 3: "agree_stage3", 4: "agree_final"}[stage]
    next_status = {2: ST_STAGE3, 3: ST_STAGE4, 4: ST_DONE}[stage]
    user = await db.update(cb.from_user.id, **{field: f"Ha ({now()})"}, status=next_status)

    if stage == 4:
        await finish_application(cb.message, cb.from_user.id, db, sheets, bot, config)
    else:
        sync.push(db, sheets, user)
        card.refresh(bot, db, config, user)
        await show_stage(cb.message, stage + 1)


@router.callback_query(F.data.startswith("decline:"))
async def cb_decline(cb: CallbackQuery, db, sheets, bot, config, **_):
    stage = int(cb.data.split(":")[1])
    await cb.answer()
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    field = {2: "agree_stage2", 3: "agree_stage3", 4: "agree_final"}[stage]
    user = await db.update(
        cb.from_user.id, **{field: f"Yo‘q ({now()})"}, status=ST_DECLINED
    )
    sync.push(db, sheets, user)
    card.refresh(bot, db, config, user)
    await cb.message.answer(t.DECLINED, reply_markup=kb.restart_kb())


# ---------------------------------------------------------------- boshqa
@router.message(Command("help"))
async def cmd_help(message: Message, **_):
    await message.answer(
        "ℹ️ <b>Yordam</b>\n\n"
        "/start — arizani boshlash yoki davom ettirish\n"
        "/status — ariza holatini ko‘rish\n"
        "/help — ushbu yordam\n\n"
        "Savollaringiz bo‘lsa, administrator bilan bog‘laning."
    )


@router.message(Command("status"))
async def cmd_status(message: Message, db, **_):
    from ..db import STATUS_LABELS

    user = await db.get(message.from_user.id)
    if not user or user.get("status") == "new":
        await message.answer("Siz hali ariza boshlamagansiz. /start bosing.")
        return
    await message.answer(
        "📋 <b>Ariza holati</b>\n\n"
        f"👤 {user.get('full_name') or '—'}\n"
        f"📞 {user.get('phone') or '—'}\n"
        f"💬 {user.get('username') or '—'}\n\n"
        f"📌 <b>Bosqich:</b> {STATUS_LABELS.get(user.get('status'), '—')}\n"
        f"🧾 <b>Chek:</b> "
        f"{ {'none':'Yuborilmagan','pending':'Tekshiruvda','approved':'Tasdiqlangan','rejected':'Rad etilgan'}.get(user.get('receipt_status'),'—') }"
    )


async def _resume_form(message: Message, state: FSMContext, user: dict) -> None:
    """Bot qayta ishga tushgach yo'qolgan anketa holatini tiklaydi."""
    if not user.get("full_name"):
        await state.set_state(Form.full_name)
        await message.answer(t.ASK_FULL_NAME, reply_markup=kb.REMOVE)
    elif not user.get("phone"):
        await state.set_state(Form.phone)
        await message.answer(t.ASK_PHONE, reply_markup=kb.phone_kb())
    else:
        await state.set_state(Form.username)
        await message.answer(
            t.ASK_USERNAME, reply_markup=kb.username_kb(message.from_user.username)
        )


@router.message(StateFilter(None), F.chat.type == "private")
async def fallback(message: Message, state: FSMContext, db, config, **_):
    """Holatsiz kelgan xabar — foydalanuvchini o'z bosqichiga qaytaramiz."""
    user = await db.get(message.from_user.id)
    status = user.get("status") if user else None

    if status == ST_RECEIPT_SENT:
        await message.answer(t.WAIT_ADMIN)
    elif status == ST_FORM:
        await _resume_form(message, state, user)
    elif status in (ST_STAGE2, ST_STAGE3, ST_STAGE4):
        stage = {ST_STAGE2: 2, ST_STAGE3: 3, ST_STAGE4: 4}[status]
        await show_stage(message, stage)
    elif status == ST_RECEIPT_WAIT:
        await message.answer(t.PROJECT_SELECT, reply_markup=kb.receipt_kb(config.irshod_url))
    elif status == ST_DONE:
        link = user.get("invite_link") if link_alive(user) else None
        await message.answer(
            t.ALREADY_DONE if link else t.LINK_EXPIRED,
            reply_markup=kb.invite_kb(link) if link else None,
        )
    else:
        await message.answer(t.UNKNOWN, reply_markup=kb.start_kb())


@router.callback_query()
async def stale_callback(cb: CallbackQuery, **_):
    """Hech bir handler ushlamagan tugma — jim qolmasin."""
    await cb.answer("Bu tugma eskirgan. /start bosing.", show_alert=True)
