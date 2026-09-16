/**
 * Asoschilar rezidentligi boti — ma'lumotlarni qabul qiluvchi skript.
 *
 * O'rnatish:
 *   1. Google Sheet → Kengaytmalar (Extensions) → Apps Script
 *   2. Bu kodni to'liq nusxalab qo'ying (eskisini o'chiring)
 *   3. Pastdagi SECRET ni o'zingizning maxfiy so'zingizga almashtiring
 *   4. Deploy → New deployment → Web app
 *        Execute as:  Me
 *        Who has access:  Anyone
 *   5. Chiqqan URL ni botning .env fayliga qo'ying
 */

const SHEET_NAME = 'Arizalar';
const SECRET = 'CHANGE_ME';           // ← shu yerni o'zgartiring

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(30000);
  } catch (err) {
    return json({ ok: false, error: 'band, keyinroq urinib ko\'ring' });
  }

  try {
    const body = JSON.parse(e.postData.contents);

    if (String(body.secret) !== String(SECRET)) {
      return json({ ok: false, error: 'maxfiy so\'z mos kelmadi' });
    }

    const sheet = getSheet(body.headers);
    const rows = body.rows || [];
    let updated = 0, inserted = 0;

    // B ustuni — Telegram ID. ID → qator raqami xaritasi.
    const lastRow = sheet.getLastRow();
    const index = {};
    if (lastRow > 1) {
      const ids = sheet.getRange(2, 2, lastRow - 1, 1).getValues();
      for (let i = 0; i < ids.length; i++) {
        const id = String(ids[i][0]).trim();
        if (id) index[id] = i + 2;
      }
    }

    for (const row of rows) {
      const id = String(row[1]).trim();
      let target = index[id];
      if (target) {
        updated++;
      } else {
        target = sheet.getLastRow() + 1;
        if (target < 2) target = 2;
        index[id] = target;
        inserted++;
      }
      row[0] = target - 1;                       // tartib raqami
      sheet.getRange(target, 1, 1, row.length).setValues([row]);
    }

    return json({ ok: true, updated: updated, inserted: inserted });
  } catch (err) {
    return json({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

function doGet() {
  return json({ ok: true, status: 'Bot skripti ishlayapti' });
}

function getSheet(headers) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) sheet = ss.insertSheet(SHEET_NAME);

  if (headers && headers.length) {
    const current = sheet.getRange(1, 1, 1, headers.length).getValues()[0];
    if (current.join('|') !== headers.join('|')) {
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
      sheet.getRange(1, 1, 1, headers.length)
        .setFontWeight('bold')
        .setBackground('#2980b9')
        .setFontColor('#ffffff')
        .setHorizontalAlignment('center');
      sheet.setFrozenRows(1);
    }
  }
  return sheet;
}

function json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
