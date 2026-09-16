"""Foydalanuvchi kiritgan ma'lumotlarni tekshirish."""
from __future__ import annotations

import re

_NAME_RE = re.compile(r"^[A-Za-zÀ-ÿʻʼ'‘’`Ѐ-ӿ\s.\-]+$")
_USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")


def clean_full_name(raw: str) -> str | None:
    """Ism familiyani tozalab qaytaradi, noto'g'ri bo'lsa None."""
    text = " ".join((raw or "").split())
    if not (4 <= len(text) <= 80):
        return None
    if len(text.split()) < 2:
        return None
    if not _NAME_RE.match(text):
        return None
    return " ".join(w.capitalize() for w in text.split())


def clean_phone(raw: str) -> str | None:
    """+998XXXXXXXXX ko'rinishiga keltiradi."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:                       # 901234567
        digits = "998" + digits
    elif len(digits) == 12 and digits.startswith("998"):
        pass
    elif len(digits) == 13 and digits.startswith("8998"):
        digits = digits[1:]
    else:
        return None
    if not digits.startswith("998"):
        return None
    operator = digits[3:5]
    if not operator.isdigit() or operator[0] not in "3789":
        return None
    return "+" + digits


def clean_username(raw: str) -> str | None:
    """@username ko'rinishiga keltiradi."""
    text = (raw or "").strip().lstrip("@").strip()
    if text.lower().startswith(("https://t.me/", "t.me/")):
        text = text.split("t.me/", 1)[1].strip("/")
    if not _USERNAME_RE.match(text):
        return None
    return "@" + text
