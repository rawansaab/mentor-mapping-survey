# app.py
# -*- coding: utf-8 -*-
import os
import re
import json
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from markupsafe import Markup
import pytz
import gspread
from google.oauth2.service_account import Credentials

# ===== יצירת האפליקציה =====
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "dev-secret-change-me")

# ------------ Maintenance (אופציונלי) ------------
@app.before_request
def maintenance_mode():
    if os.getenv("MAINTENANCE_MODE", "0") == "1":
        html = """
        <html lang="he" dir="rtl">
        <head>
          <meta charset="utf-8">
          <title>האתר סגור</title>
          <style>
            body{
              font-family:system-ui,-apple-system,Segoe UI,Heebo,Arial;
              background:#f8fafc;
              direction:rtl;
              text-align:center;
              margin:0;
              padding-top:120px;
              color:#111827;
            }
            .box{
              display:inline-block;
              padding:32px 40px;
              border-radius:18px;
              background:#ffffff;
              box-shadow:0 10px 30px rgba(15,23,42,.08);
              border:1px solid #e5e7eb;
            }
            h1{margin:0 0 12px;font-size:26px;}
            p{margin:0;color:#6b7280;}
          </style>
        </head>
        <body>
          <div class="box">
            <h1>⚙️ האתר סגור כרגע</h1>
            <p>הגישה לטופס סטודנטים הוגבלה זמנית.</p>
          </div>
        </body>
        </html>
        """
        return Markup(html), 503

# ===== קונפיגורציה כללית =====
SPECIALIZATIONS = [
    "רווחה", "מוגבלות", "זקנה", "ילדים ונוער", "בריאות הנפש",
    "שיקום", "משפחה", "נשים", "בריאות", "קהילה"
]

COLUMNS_ORDER = [
    "תאריך שליחה", "שם פרטי", "שם משפחה", "סטטוס מדריך", "מוסד", "תחום התמחות",
    "רחוב", "עיר", "מיקוד", "מספר סטודנטים שניתן לקלוט (1 או 2)",
    "מעוניין להמשיך", "בקשות מיוחדות", "חוות דעת - נקודות",
    "חוות דעת - טקסט חופשי", "טלפון", "אימייל"
]

# ===== חיבור ל-Google Sheets =====
def get_worksheet():
    """
    מצפה ל:
    - GOOGLE_SERVICE_ACCOUNT_JSON : תוכן מלא של קובץ ה-JSON
    - SPREADSHEET_ID              : ה-ID של הגיליון (לא ה-URL)
    """
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON env var is missing")

    sheet_id = os.environ.get("SPREADSHEET_ID")
    if not sheet_id:
        raise RuntimeError("SPREADSHEET_ID env var is missing")

    # JSON מה־env
    try:
        creds_dict = json.loads(creds_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)

    try:
        sh = gc.open_by_key(sheet_id)
    except Exception as e:
        raise RuntimeError(f"Failed to open spreadsheet by key: {e}")

    return sh.sheet1


def ensure_header(ws):
    existing = ws.get_all_values()
    if not existing or existing[0] != COLUMNS_ORDER:
        ws.clear()
        ws.append_row(COLUMNS_ORDER)

# ===== ראוט ראשי =====
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        f = request.form
        errors = []

        # ולידציה
        if not f.get("first_name"):
            errors.append("יש למלא שם פרטי.")
        if not f.get("last_name"):
            errors.append("יש למלא שם משפחה.")
        if f.get("mentor_status", "") == "":
            errors.append("יש לבחור סטטוס מדריך.")
        if not f.get("institute"):
            errors.append("יש למלא שם מוסד.")
        if f.get("specialization") in ("", "בחר/י מהרשימה"):
            errors.append("יש לבחור תחום התמחות.")
        if not f.get("street"):
            errors.append("יש למלא רחוב.")
        if not f.get("city"):
            errors.append("יש למלא עיר.")
        if not f.get("postal_code"):
            errors.append("יש למלא מיקוד.")

        # טלפון
        phone_raw = f.get("phone", "")
        phone = phone_raw.replace("-", "").replace(" ", "")
        if not re.match(r"^(0?5\d{8})$", phone):
            errors.append("מספר טלפון לא תקין (דוגמה: 0501234567).")

        # מייל
        email = f.get("email", "").strip()
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors.append("כתובת דוא\"ל לא תקינה.")

        # מספר סטודנטים
        num_students_raw = f.get("num_students", "1").strip()
        if num_students_raw not in ("1", "2"):
            errors.append("יש לבחור מספר סטודנטים 1 או 2.")
        else:
            num_students = int(num_students_raw)

        if errors:
            for e in errors:
                flash(e, "error")
            return redirect(url_for("index"))

        # בניית רשומה
        tz = pytz.timezone("Asia/Jerusalem")
        record = {
            "תאריך שליחה": datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
            "שם פרטי": f.get("first_name", "").strip(),
            "שם משפחה": f.get("last_name", "").strip(),
            "סטטוס מדריך": f.get("mentor_status", "").strip(),
            "מוסד": f.get("institute", "").strip(),
            "תחום התמחות": f.get("specialization", "").strip(),
            "רחוב": f.get("street", "").strip(),
            "עיר": f.get("city", "").strip(),
            "מיקוד": f.get("postal_code", "").strip(),
            "מספר סטודנטים שניתן לקלוט (1 או 2)": num_students,
            "מעוניין להמשיך": f.get("continue_mentoring", "").strip(),
            "בקשות מיוחדות": f.get("special_requests", "").strip(),
            "חוות דעת - נקודות": "; ".join(f.getlist("mentor_feedback_points")),
            "חוות דעת - טקסט חופשי": f.get("mentor_feedback_text", "").strip(),
            "טלפון": phone,
            "אימייל": email
        }

        # שמירה ל-Google Sheets
        try:
            ws = get_worksheet()
            ensure_header(ws)
            ws.append_row([record[col] for col in COLUMNS_ORDER])
            flash("✅ הטופס נשלח ונשמר בהצלחה! תודה 🌟", "success")

        except Exception as e:
            import traceback
            print("Google Sheets append error:", e)
            traceback.print_exc()  # ידפיס את כל פרטי השגיאה בלוגים של Render
            flash(f"❌ שגיאה בשמירה לגיליון: {e}", "error")

        return redirect(url_for("index"))

    # GET
    return render_template("index.html", specializations=SPECIALIZATIONS)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

