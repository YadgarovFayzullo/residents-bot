# Asoschilar rezidentligi boti

Telegram: [@Asoschilarrezidentligibot](https://t.me/Asoschilarrezidentligibot)

Ariza voronkasi: **/start → anketa → chek → admin tekshiruvi → 2/3/4-bosqich rozilik → yopiq guruh havolasi**, barcha ma'lumotlar Google Sheets'ga yoziladi.

---

## Ishga tushirish

```bash
./run.sh
```

Birinchi ishga tushishda `.venv` avtomatik yaratiladi.

---

## Sozlash — 4 ta qadam

### 1. Admin ID larini olish

Botga **/myid** yozing → ID ni `.env` faylidagi `ADMIN_IDS` ga qo'ying.
Bir nechta admin bo'lsa, vergul bilan: `ADMIN_IDS=123456,789012`

Adminlar chekni tasdiqlaydi/rad etadi va `/admin` panelidan foydalanadi.

### 2. Yopiq guruhni ulash

1. Botni yopiq guruhga qo'shing
2. Guruhda botga **admin** huquqini bering — «Invite users via link» yoqilgan bo'lsin
3. Guruhda **/myid** yozing → chiqqan `Chat ID` ni `.env` dagi `PRIVATE_GROUP_ID` ga qo'ying (manfiy son, masalan `-1001234567890`)

Busiz yakuniy bir martalik havola yaratilmaydi.

### 3. Cheklar arxivini ulash

Har bir chek yopiq kanalga nusxalanadi — shu bois uni **istalgan vaqtda** ochib
ko'rish mumkin (Telegram fayllarni o'zida saqlaydi, serverda joy egallamaydi).

1. Telegramda **yopiq kanal** oching (masalan «Cheklar arxivi»)
2. Botni kanalga qo'shing va **admin** qiling
3. Bot sizga kanal ID sini yuboradi → uni `.env` dagi `RECEIPT_ARCHIVE_ID` ga yozing
4. Botni qayta ishga tushiring, `/arxiv` bilan tekshiring

Har bir chek uchun jadvaldagi **«Chek (arxiv)»** ustunida bosiladigan havola
paydo bo'ladi. `RECEIPT_ARCHIVE_ID` bo'sh qolsa, `ADMIN_GROUP_ID` arxiv
sifatida ishlatiladi; ikkalasi ham bo'sh bo'lsa — havola saqlanmaydi.

> Ustun yangi qo'shilgani uchun eski qatorlarni bir marta `/resync` bilan
> qayta yozdiring.

### 4. Google Sheets ulash

1. [Google Cloud Console](https://console.cloud.google.com/) → yangi loyiha
2. **APIs & Services → Library** → `Google Sheets API` va `Google Drive API` ni yoqing
3. **Credentials → Create credentials → Service account** → yarating
4. Service account → **Keys → Add key → JSON** → faylni yuklab oling
5. Faylni loyiha papkasiga **`credentials.json`** nomi bilan joylang
6. JSON ichidagi `client_email` (masalan `bot@loyiha.iam.gserviceaccount.com`) manzilini nusxalang
7. [Google Sheet](https://docs.google.com/spreadsheets/d/1k98SgZ12ttcWGHiRpFLMyVTpeUziSOIy5FjpNqLjPf4/edit) ni oching → **Share** → shu emailga **Editor** huquqini bering

Sarlavhalar va `Arizalar` varag'i birinchi yozuvda avtomatik yaratiladi.

> Sheets ulanmagan bo'lsa ham bot to'liq ishlaydi — yozuvlar SQLite'da to'planadi.
> Keyin ulaganingizda `/sync` buyrug'i hammasini jadvalga ko'chiradi.

---

## Buyruqlar

**Foydalanuvchi**
| Buyruq | Vazifasi |
|---|---|
| `/start` | Arizani boshlash yoki to'xtagan joydan davom ettirish |
| `/status` | O'z ariza holatini ko'rish |
| `/help` | Yordam |

**Admin**
| Buyruq | Vazifasi |
|---|---|
| `/admin` | Panel: statistika, kutilayotgan cheklar, sinxronlash |
| `/chek <ID / ism / telefon / @username>` | Saqlangan chekni qayta ochish |
| `/arxiv` | Chek arxivi ulanganini tekshirish |
| `/sync` | Sheets'ga yozilmagan yozuvlarni ko'chirish |
| `/resync` | Jadvaldagi **barcha** qatorlarni qayta yozish |
| `/broadcast` | Barcha foydalanuvchilarga e'lon |
| `/myid` | O'z ID va chat ID sini bilish |

---

## Voronka

| Bosqich | Nima bo'ladi |
|---|---|
| 0 | Dastur haqida ma'lumot + **🚀 Start** tugmasi |
| 1 | Ism familiya → telefon → Telegram username |
| — | Irshod.uz'dan loyiha tanlash + **🧾 Chekni yuborish** |
| — | Chek (rasm yoki PDF) → adminlarga tushadi va arxiv kanaliga saqlanadi |
| — | Admin **✅ Tasdiqlash** / **❌ Rad etish** (sabab bilan) |
| 2 | 61 kunlik dastur → **✅ Roziman** |
| 3 | Rezidentlik, 3% ulush → **✅ Roziman** |
| 4 | Yakuniy umumiy rozilik → **✅ Ha, barcha shartlarga roziman** |
| ✅ | 🎉 Ariza yakunlandi + **bir martalik** yopiq guruh havolasi |

**Jadval har qadamda yangilanadi** — foydalanuvchi `/start` bosishi bilanoq qator
paydo bo'ladi, keyin ism, telefon, username, chek va har bir rozilik darhol
yoziladi. Shu bois adminlar ariza aynan qaysi bosqichda to'xtaganini ko'radi:
**«Ariza holati»** ustuni bosqichni, **«Oxirgi harakat»** ustuni esa oxirgi
harakat vaqtini ko'rsatadi. Yozuv fon rejimida ketadi — bot sekinlashmaydi, va
Sheets javob bermasa yozuv SQLite'da qoladi (`/sync` keyin ko'chiradi).

Rad etilgan chek qayta yuborilishi mumkin. Bot qayta ishga tushsa ham foydalanuvchi to'xtagan bosqichidan davom etadi.

---

## Testlar

```bash
for f in tests/test_*.py; do .venv/bin/python "$f"; done
```

172 ta tekshiruv — butun voronka, admin oqimi va chekka holatlar (guruh ulanmagan, bot admin emas, takroriy tugma bosish, begona odam tugmani bosishi), chek arxivi, har qadamdagi sinxronizatsiya va Sheets webhook'i.

---

## Fayllar

```
bot/
  main.py          ishga tushirish
  config.py        .env sozlamalari
  db.py            SQLite (arizalar manbasi)
  sheets.py        Google Sheets sinxronizatsiyasi
  archive.py       cheklar arxivi (kanal havolalari)
  sync.py          har qadamda Sheets'ga yozish (fon rejimida)
  texts.py         barcha matnlar — o'zgartirish shu yerda
  keyboards.py     tugmalar
  validators.py    ism/telefon/username tekshiruvi
  states.py        FSM holatlari
  middlewares.py   db/sheets/config ni handlerlarga uzatish
  handlers/
    user.py        foydalanuvchi voronkasi
    admin.py       chek tekshiruvi, panel, e'lon
data/bot.db        ma'lumotlar bazasi
```

Matnlarni o'zgartirish uchun faqat `bot/texts.py` ni tahrirlang.
