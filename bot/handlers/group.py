"""Bot guruhga qo'shilganda guruh ID sini avtomatik eslab qoladi."""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated, Message

log = logging.getLogger(__name__)
router = Router(name="group")

GROUP_KEY = "private_group_id"


async def resolve_group_id(db, config) -> int | None:
    """Guruh ID: avval .env, bo'lmasa bazadagi avtomatik topilgani."""
    if config.private_group_id:
        return config.private_group_id
    saved = await db.get_setting(GROUP_KEY)
    if saved and saved.lstrip("-").isdigit():
        return int(saved)
    return None


@router.my_chat_member()
async def on_bot_status_changed(event: ChatMemberUpdated, db, bot, config, **_):
    """Bot guruhga qo'shilganda / admin qilinganda ishga tushadi."""
    chat = event.chat
    status = event.new_chat_member.status

    # Kanal — cheklar arxivi uchun ishlatiladi
    if chat.type == "channel":
        if status in ("administrator", "member"):
            text = (
                "🗂 <b>Bot kanalga qo‘shildi</b>\n\n"
                f"📛 <b>Kanal:</b> {chat.title}\n"
                f"🆔 <b>ID:</b> <code>{chat.id}</code>\n\n"
                + ("Bu ID ni <code>.env</code> dagi <code>RECEIPT_ARCHIVE_ID</code> ga "
                   "yozing va botni qayta ishga tushiring — cheklar shu yerga saqlanadi."
                   if status == "administrator" else
                   "Endi botni <b>admin</b> qiling (xabar yuborish huquqi bilan).")
            )
        else:
            return
        for admin_id in config.admin_ids:
            try:
                await bot.send_message(admin_id, text)
            except Exception:
                pass
        return

    if chat.type not in ("group", "supergroup"):
        return

    can_invite = bool(getattr(event.new_chat_member, "can_invite_users", False))

    # Arxiv guruhini yopiq guruh deb yozib qo'ymaymiz
    if chat.id == config.receipt_archive_id:
        return

    # Yopiq guruh allaqachon ulangan bo'lsa — yangisini bosib o'tmaymiz
    known = await resolve_group_id(db, config)
    if status == "administrator" and known and known != chat.id:
        text = (
            "🗂 <b>Bot yangi guruhga admin qilindi</b>\n\n"
            f"📛 <b>Guruh:</b> {chat.title}\n"
            f"🆔 <b>ID:</b> <code>{chat.id}</code>\n\n"
            f"Yopiq guruh o‘zgarmadi (<code>{known}</code>).\n"
            "Agar bu guruh <b>cheklar arxivi</b> uchun bo‘lsa, yuqoridagi ID ni "
            "<code>.env</code> dagi <code>RECEIPT_ARCHIVE_ID</code> ga yozing."
        )
        for admin_id in config.admin_ids:
            try:
                await bot.send_message(admin_id, text)
            except Exception:
                pass
        return

    if status == "administrator" and can_invite:
        await db.set_setting(GROUP_KEY, str(chat.id))
        log.info("Yopiq guruh eslab qolindi: %s (%s)", chat.title, chat.id)
        text = (
            "✅ <b>Yopiq guruh ulandi</b>\n\n"
            f"📛 <b>Guruh:</b> {chat.title}\n"
            f"🆔 <b>ID:</b> <code>{chat.id}</code>\n\n"
            "Endi arizani yakunlagan foydalanuvchilarga bir martalik "
            "taklif havolalari shu guruhga beriladi.\n\n"
            "<i>Agar bu guruhni cheklar arxivi qilmoqchi bo‘lsangiz — yuqoridagi "
            "ID ni <code>RECEIPT_ARCHIVE_ID</code> ga yozing.</i>"
        )
    elif status == "administrator":
        text = (
            "⚠️ <b>Bot admin qilindi, lekin huquq yetarli emas</b>\n\n"
            f"📛 <b>Guruh:</b> {chat.title}\n\n"
            "Bot sozlamalarida <b>«Foydalanuvchilarni havola orqali taklif qilish»</b> "
            "huquqini yoqing — busiz taklif havolasi yaratilmaydi."
        )
    elif status in ("member", "restricted"):
        text = (
            "ℹ️ <b>Bot guruhga qo‘shildi</b>\n\n"
            f"📛 <b>Guruh:</b> {chat.title}\n\n"
            "Endi botni <b>admin</b> qiling va «Foydalanuvchilarni havola orqali "
            "taklif qilish» huquqini bering."
        )
    elif status in ("left", "kicked"):
        saved = await db.get_setting(GROUP_KEY)
        if saved == str(chat.id):
            await db.set_setting(GROUP_KEY, "")
        text = (
            "🚫 <b>Bot guruhdan chiqarildi</b>\n\n"
            f"📛 <b>Guruh:</b> {chat.title}\n\n"
            "Taklif havolalari endi yaratilmaydi."
        )
    else:
        return

    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass


@router.message(Command("group"))
async def cmd_group(message: Message, db, bot, config, **_):
    """Ulangan guruhni tekshirish (faqat adminlar uchun)."""
    if not config.is_admin(message.from_user.id):
        return
    gid = await resolve_group_id(db, config)
    if not gid:
        await message.answer(
            "🔴 <b>Yopiq guruh ulanmagan</b>\n\n"
            "Botni guruhga qo‘shing va admin qiling — "
            "«Foydalanuvchilarni havola orqali taklif qilish» huquqi bilan. "
            "Guruh avtomatik ulanadi."
        )
        return
    try:
        chat = await bot.get_chat(gid)
        me = await bot.get_chat_member(gid, (await bot.get_me()).id)
        ok = getattr(me, "can_invite_users", False)
        await message.answer(
            f"{'🟢' if ok else '🟡'} <b>Yopiq guruh</b>\n\n"
            f"📛 {chat.title}\n"
            f"🆔 <code>{gid}</code>\n"
            f"👤 Bot holati: {me.status}\n"
            f"🔗 Havola yaratish huquqi: {'bor ✅' if ok else 'YO‘Q ❌'}"
        )
    except Exception as e:
        await message.answer(
            f"🔴 Guruhga ulanib bo‘lmadi: <code>{e}</code>\n\n"
            f"Saqlangan ID: <code>{gid}</code>"
        )
