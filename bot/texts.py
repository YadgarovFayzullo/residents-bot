"""Botning barcha matnlari (o'zbek tilida)."""
from __future__ import annotations

# ---------------------------------------------------------------- 0-BOSQICH
WELCOME = (
    "<b>Asoschilar rezidentligi dasturiga xush kelibsiz!</b>\n\n"
    "<i>Loyiha bizdan. Ijro sizdan.</i>\n\n"
    "Startup boshlash uchun har doim ham yangi g‘oya o‘ylab topish shart emas.\n\n"
    "Ba’zan ishlashi mumkin bo‘lgan to‘g‘ri loyihani tanlash va uni sifatli "
    "ijro etishning o‘zi yetarli.\n\n"
    "👍 Startup Garage sizga global bozorda shakllangan va mahalliy bozor uchun "
    "moslashtirish mumkin bo‘lgan loyihalar orasidan tanlash imkonini beradi."
)

# ---------------------------------------------------------------- 1-BOSQICH
ASK_FULL_NAME = (
    "<b>1-BOSQICH — Ariza ma’lumotlari</b>\n\n"
    "✍️ Ism va familiyangizni to‘liq yozing.\n\n"
    "<i>Masalan: Abdulaziz Karimov</i>"
)
ERR_FULL_NAME = (
    "❗️ Ism va familiya faqat harflardan iborat bo‘lishi va kamida 2 ta so‘z "
    "bo‘lishi kerak.\n\nIltimos, qaytadan kiriting.\n\n<i>Masalan: Abdulaziz Karimov</i>"
)

ASK_PHONE = (
    "📞 Telefon raqamingizni yuboring.\n\n"
    "Pastdagi <b>«📱 Raqamni yuborish»</b> tugmasini bosing yoki raqamni qo‘lda yozing.\n\n"
    "<i>Masalan: +998901234567</i>"
)
ERR_PHONE = (
    "❗️ Telefon raqam noto‘g‘ri kiritildi.\n\n"
    "Iltimos, O‘zbekiston raqamini quyidagi ko‘rinishda yozing:\n"
    "<i>+998901234567</i>"
)

ASK_USERNAME = (
    "💬 Telegram username’ingizni yuboring.\n\n"
    "Agar username’ingiz mavjud bo‘lsa, pastdagi tugmani bosing yoki "
    "<code>@username</code> ko‘rinishida yozing.\n\n"
    "Username’ingiz bo‘lmasa — <b>«Username yo‘q»</b> tugmasini bosing."
)
ERR_USERNAME = (
    "❗️ Username noto‘g‘ri. U 5–32 ta belgidan iborat bo‘lib, faqat harflar, "
    "raqamlar va pastki chiziqdan tashkil topishi kerak.\n\n"
    "<i>Masalan: @startupgarage</i>"
)

# ---------------------------------------------------------------- Chek
PROJECT_SELECT = (
    "<b>1 - bosqichga xush kelibsiz!</b> Ushbu bosqichda loyihani tanlab olishingiz "
    "lozim buning uchun;\n\n"
    "Irshod.uz platformasidan o‘zingizga mos loyihani tanlashingiz va ushbu loyiha "
    "uchun <b>Playbook</b>’ni xarid qilib, chekni botga jo‘natishingiz lozim.\n\n"
    "👇 Chekni yuborish uchun quyidagi tugmani bosing."
)

ASK_RECEIPT = (
    "🧾 <b>Chekni yuboring</b>\n\n"
    "To‘lov chekini rasm (screenshot) yoki PDF fayl ko‘rinishida yuboring.\n\n"
    "❗️ Chek aniq va to‘liq ko‘rinadigan bo‘lsin — summa, sana va to‘lov "
    "ma’lumotlari o‘qilishi kerak."
)
ERR_RECEIPT = (
    "❗️ Iltimos, chekni <b>rasm</b> yoki <b>PDF fayl</b> ko‘rinishida yuboring.\n\n"
    "Matn yoki boshqa turdagi fayllar qabul qilinmaydi."
)

RECEIPT_RECEIVED = (
    "✅ Chekingiz qabul qilindi!\n\n"
    "⏳ Hozirda admin tomonidan tekshirilmoqda. Tekshiruv yakunlangach, "
    "sizga xabar beramiz.\n\n"
    "<i>Odatda bu 24 soat ichida amalga oshiriladi.</i>"
)

RECEIPT_APPROVED = (
    "✅ <b>Chek tasdiqlandi!</b>\n\n"
    "Tabriklaymiz — to‘lovingiz muvaffaqiyatli tasdiqlandi. "
    "Endi keyingi bosqichga o‘tamiz."
)


def receipt_rejected(reason: str | None) -> str:
    text = (
        "❌ <b>Chek tasdiqlanmadi</b>\n\n"
        "Afsuski, yuborilgan chek qabul qilinmadi."
    )
    if reason:
        text += f"\n\n<b>Sabab:</b> {reason}"
    text += (
        "\n\nIltimos, to‘g‘ri chekni qaytadan yuboring. "
        "Savollar bo‘lsa, administrator bilan bog‘laning."
    )
    return text


# ---------------------------------------------------------------- 2-BOSQICH
STAGE_2 = (
    "<b>2-BOSQICH — 61 kunlik amaliy dastur</b>\n\n"
    "Tanlangan loyihani <b>61 kun</b> davomida tajribali asoschi-trackerlar bilan "
    "«G‘oyadan investitsiyagacha» nomli <b>12 mavzudan</b> iborat online va offline "
    "mentorlik sessiyalarida birgalikda amalga oshirasiz.\n\n"
    "Ushbu davrda quyidagilar bo‘yicha amaliy yordam olasiz:\n"
    "• Loyiha strategiyasi\n"
    "• MVP yaratish\n"
    "• Bozorni sinash\n"
    "• Dastlabki mijozlarni topish\n"
    "• Loyihani rivojlantirish\n\n"
    "❓ <b>Ushbu dasturda qatnashishga rozimisiz?</b>"
)

# ---------------------------------------------------------------- 3-BOSQICH
STAGE_3 = (
    "<b>3-BOSQICH — Startup Garage rezidenti bo‘lish</b>\n\n"
    "Loyiha muvaffaqiyatli yo‘lga qo‘yilgan taqdirda, siz <b>Startup Garage "
    "rezidenti</b> bo‘lish imkoniyatiga ega bo‘lasiz.\n\n"
    "Buning evaziga startup loyihaning <b>3% ulushi</b> Startup Garage’ga beriladi.\n\n"
    "❓ <b>Ushbu shartga rozimisiz?</b>"
)

# ---------------------------------------------------------------- 4-BOSQICH
STAGE_4 = (
    "<b>4-BOSQICH — Yakuniy umumiy rozilik</b>\n\n"
    "Siz quyidagilarni tasdiqladingiz:\n"
    "1️⃣ Ariza ma’lumotlari va Playbook to‘lovi\n"
    "2️⃣ 61 kunlik amaliy dasturda qatnashish\n"
    "3️⃣ Startup Garage rezidentligi — 3% ulush sharti\n\n"
    "❓ <b>Yuqoridagi barcha shartlarga rozilik bildirasizmi?</b>"
)

DECLINED = (
    "Tushunarli 🙏\n\n"
    "Arizangiz to‘xtatildi. Fikringiz o‘zgarsa, istalgan vaqtda /start buyrug‘i "
    "orqali qaytadan boshlashingiz mumkin."
)

# ---------------------------------------------------------------- Yakun
def _days(n: int) -> str:
    return f"{n} kun"


def finished(days: int) -> str:
    return (
        "🎉 <b>Ariza yakunlandi!</b>\n\n"
        "Tabriklaymiz — siz <b>Asoschilar rezidentligi</b> dasturiga muvaffaqiyatli "
        "ro‘yxatdan o‘tdingiz.\n\n"
        "👇 Quyidagi havola orqali yopiq guruhga qo‘shiling.\n\n"
        "⚠️ Havola <b>faqat siz uchun</b>, <b>bir marta</b> ishlaydi va "
        f"<b>{_days(days)}</b>dan keyin bekor bo‘ladi."
    )


def link_renewed(days: int) -> str:
    return (
        "🔄 <b>Havola yangilandi</b>\n\n"
        "Avvalgi havolangiz muddati tugagan edi, sizga yangisi berildi.\n\n"
        f"⚠️ Bu havola ham <b>bir marta</b> ishlaydi va <b>{_days(days)}</b>dan "
        "keyin bekor bo‘ladi."
    )


LINK_EXPIRED = (
    "⏳ Taklif havolangiz muddati tugagan.\n\n"
    "Yangi havola olish uchun /start buyrug‘ini yuboring."
)

FINISHED_NO_LINK = (
    "🎉 <b>Ariza yakunlandi!</b>\n\n"
    "Tabriklaymiz — siz <b>Asoschilar rezidentligi</b> dasturiga muvaffaqiyatli "
    "ro‘yxatdan o‘tdingiz.\n\n"
    "⏳ Yopiq guruhga qo‘shilish havolasi tez orada yuboriladi."
)

ALREADY_DONE = (
    "✅ Siz allaqachon ro‘yxatdan o‘tgansiz.\n\n"
    "Yopiq guruhga qo‘shilish havolangiz quyida. "
    "Savollar bo‘lsa, administrator bilan bog‘laning."
)

WAIT_ADMIN = (
    "⏳ Chekingiz hali admin tomonidan tekshirilmoqda.\n\n"
    "Tekshiruv yakunlangach, sizga darhol xabar beramiz."
)

UNKNOWN = (
    "🤖 Buyruq tushunarsiz.\n\n"
    "Ariza jarayonini davom ettirish uchun /start buyrug‘ini yuboring."
)


def summary(data: dict) -> str:
    return (
        "<b>Ma’lumotlaringiz:</b>\n\n"
        f"👤 <b>Ism familiya:</b> {data.get('full_name', '—')}\n"
        f"📞 <b>Telefon:</b> {data.get('phone', '—')}\n"
        f"💬 <b>Username:</b> {data.get('username', '—')}"
    )
