"""Inline va reply klaviaturalar."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

REMOVE = ReplyKeyboardRemove()


def start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🚀 Start", callback_data="start_form")]]
    )


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="+998901234567",
    )


def username_kb(tg_username: str | None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if tg_username:
        kb.button(text=f"✅ @{tg_username}", callback_data="use_tg_username")
    kb.button(text="🚫 Username yo‘q", callback_data="no_username")
    kb.adjust(1)
    return kb.as_markup()


def receipt_kb(irshod_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Irshod.uz platformasi", url=irshod_url)],
            [InlineKeyboardButton(text="🧾 Chekni yuborish", callback_data="send_receipt")],
        ]
    )


def agree_kb(stage: int) -> InlineKeyboardMarkup:
    """2/3/4-bosqich rozilik tugmalari."""
    yes_text = "✅ Ha, barcha shartlarga roziman" if stage == 4 else "✅ Roziman"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=yes_text, callback_data=f"agree:{stage}")],
            [InlineKeyboardButton(text="❌ Rozi emasman", callback_data=f"decline:{stage}")],
        ]
    )


def review_kb(user_id: int) -> InlineKeyboardMarkup:
    """Admin uchun chekni tekshirish tugmalari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"ok:{user_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"no:{user_id}"),
            ]
        ]
    )


def invite_kb(link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Yopiq guruhga qo‘shilish", url=link)]
        ]
    )


def restart_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Qaytadan boshlash", callback_data="start_form")]
        ]
    )


def admin_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Statistika", callback_data="adm:stats")
    kb.button(text="⏳ Kutilayotgan cheklar", callback_data="adm:pending")
    kb.button(text="🔄 Sheets’ga sinxronlash", callback_data="adm:sync")
    kb.adjust(1)
    return kb.as_markup()
