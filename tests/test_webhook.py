"""Webhook rejimini soxta Apps Script serverida sinash."""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aiohttp import web
from bot.sheets import SheetsSync, HEADERS

TABLE = {}          # soxta jadval: user_id -> qator
SECRET = "maxfiy123"
PASS = FAIL = 0

def check(label, cond, extra=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}" + (f"  {extra}" if extra else ""))
    else:    FAIL += 1; print(f"  ❌ {label}  {extra}")

async def handle_post(request):
    body = await request.json()
    if str(body.get("secret")) != SECRET:
        return web.json_response({"ok": False, "error": "maxfiy so'z mos kelmadi"})
    if body.get("headers") != HEADERS:
        return web.json_response({"ok": False, "error": "sarlavhalar mos emas"})
    upd = ins = 0
    for row in body["rows"]:
        uid = str(row[1]).strip()   # Apps Script: String(row[1]).trim()
        if uid in TABLE: upd += 1
        else: ins += 1
        TABLE[uid] = row
    return web.json_response({"ok": True, "updated": upd, "inserted": ins})

async def handle_get(request):
    return web.json_response({"ok": True, "status": "ishlayapti"})

async def handle_broken(request):
    return web.Response(text="<html>Google xatosi</html>", status=500)

async def main():
    app = web.Application()
    app.router.add_post("/exec", handle_post)
    app.router.add_get("/exec", handle_get)
    app.router.add_route("*", "/broken", handle_broken)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8899); await site.start()
    url = "http://127.0.0.1:8899/exec"

    print("\n【1】 Ulanishni tekshirish (check)")
    s = SheetsSync("", "yo'q.json", "Arizalar", url, SECRET)
    check("rejim = webhook", s.mode == "webhook")
    check("enabled = True", s.enabled is True)
    ok, info = await s.check()
    check("check() muvaffaqiyatli", ok, f"-> {info}")

    print("\n【2】 Yangi yozuv qo'shish")
    u = {"user_id": 1001, "full_name": "Ali Valiyev", "phone": "+998901234567",
         "username": "@aliuz", "created_at": "2026-09-10 15:00:00",
         "receipt_status": "pending", "status": "receipt_sent"}
    r = await s.upsert(u)
    check("upsert xatosiz", s.last_error is None, f"-> {s.last_error}")
    check("jadvalda 1 ta qator", len(TABLE) == 1)
    check("ism to'g'ri yozildi", TABLE["1001"][2] == "Ali Valiyev", f"-> {TABLE["1001"][2]}")
    check("chek holati tarjima qilindi", TABLE["1001"][6] == "Tekshiruvda", f"-> {TABLE["1001"][6]}")
    check("ustunlar soni mos", len(TABLE["1001"]) == len(HEADERS))

    print("\n【3】 Mavjud yozuvni yangilash (dublikat bo'lmasligi kerak)")
    u.update(receipt_status="approved", status="done", invite_link="https://t.me/+abc")
    await s.upsert(u)
    check("qatorlar soni oshmadi", len(TABLE) == 1, f"-> {len(TABLE)} ta")
    check("holat yangilandi", TABLE["1001"][6] == "Tasdiqlangan", f"-> {TABLE["1001"][6]}")
    check("havola yozildi", TABLE["1001"][16] == "https://t.me/+abc")

    print("\n【4】 Ikkinchi foydalanuvchi")
    await s.upsert({"user_id": 2002, "full_name": "Bek Bekov", "status": "stage2"})
    check("2 ta alohida qator", len(TABLE) == 2)

    print("\n【5】 Noto'g'ri maxfiy so'z")
    bad = SheetsSync("", "yo'q.json", "Arizalar", url, "notogri")
    r = await bad.upsert({"user_id": 3003, "full_name": "X"})
    check("yozuv rad etildi", r is None)
    check("xato saqlandi", "maxfiy" in (bad.last_error or ""), f"-> {bad.last_error}")
    check("jadvalga tegmadi", len(TABLE) == 2)

    print("\n【6】 Server yiqilgan holat (bot to'xtamasligi kerak)")
    dead = SheetsSync("", "yo'q.json", "Arizalar", "http://127.0.0.1:8899/broken", SECRET)
    r = await dead.upsert({"user_id": 4004, "full_name": "Y"})
    check("upsert None qaytardi, yiqilmadi", r is None)
    check("xato yozib olindi", "500" in (dead.last_error or ""), f"-> {dead.last_error}")
    ok, info = await dead.check()
    check("check() False qaytardi", ok is False)

    print("\n【7】 Server umuman yo'q")
    off = SheetsSync("", "yo'q.json", "Arizalar", "http://127.0.0.1:9999/exec", SECRET)
    r = await off.upsert({"user_id": 5005})
    check("bot yiqilmadi", r is None)
    ok, _ = await off.check()
    check("check() False", ok is False)

    print("\n【8】 Sheets butunlay o'chirilgan")
    none_s = SheetsSync("", "yo'q.json", "Arizalar", "", "")
    check("rejim = off", none_s.mode == "off")
    check("upsert None", (await none_s.upsert({"user_id": 1})) is None)

    await runner.cleanup()
    print("\n" + "="*60)
    print(f"NATIJA:  ✅ {PASS} ta o'tdi   ❌ {FAIL} ta xato")
    print("="*60)
    return FAIL

sys.exit(asyncio.run(main()))
