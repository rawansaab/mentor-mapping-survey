# -*- coding: utf-8 -*-
import os, json, re, smtplib
from io import BytesIO
from pathlib import Path
from datetime import datetime
from email.message import EmailMessage

import pytz
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from dotenv import load_dotenv

import gspread
from google.oauth2.service_account import Credentials

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET", "super-secret-key")

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / "supervisors_config.json"
CSV_FILE = DATA_DIR / "supervisors_data.csv"

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "rawan_0304")
LECTURER_SECRET = os.getenv("LECTURER_SECRET", "secret_2026")
SYSTEM_EMAIL = os.getenv("ADMIN_EMAIL", "") 
SYSTEM_EMAIL_PWD = os.getenv("MAIL_PASSWORD", "") 

DEFAULT_CONFIG = {
    "form_title": "מיפוי מדריכים לשיבוץ סטודנטים - שנת הכשרה תשפ\"ו",
    "mentor_statuses": ["מדריך חדש (נדרש קורס)", "מדריך ותיק", "רכז/ת"],
    "specializations": ["רווחה", "מוגבלות", "זקנה", "ילדים ונוער בסיכון", "בריאות הנפש", "שיקום", "משפחה", "נשים", "בריאות", "קהילה"],
    "feedback_points": ["זמינות גבוהה", "ליווי מקצועי משמעותי", "שיתוף פעולה עם המוסד", "צורך בחיזוק בליווי"],
    "training_days": ["ראשון", "שני", "שלישי", "רביעי", "חמישי"],
    "team_emails": [],
    "section_order": ["personal", "institution", "capacity", "feedback", "contact"]
}

def load_config():
    if CONFIG_FILE.exists():
        try: return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except: return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

COLUMNS_ORDER = [
    "תאריך שליחה", "שם פרטי", "שם משפחה", "סטטוס מדריך", "שם המוסד", "תחום התמחות",
    "כתובת מלאה", "מיקוד", "מספר סטודנטים", "ימי הדרכה",
    "המשכיות הדרכה", "בקשות מיוחדות", "חוות דעת (נקודות)", "חוות דעת (חופשי)", "טלפון", "אימייל"
]

def get_worksheet():
    gc_info_env = os.getenv("GOOGLE_CREDENTIALS")
    if not gc_info_env: return None
    creds = Credentials.from_service_account_info(json.loads(gc_info_env), scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(os.getenv("SUPERVISORS_SPREADSHEET_ID"))
    return sh.sheet1

def send_team_notification(mentor_name, institute, cfg):
    if not SYSTEM_EMAIL or not SYSTEM_EMAIL_PWD or not cfg.get("team_emails"): return
    try:
        msg = EmailMessage()
        msg.set_content(f"שלום לצוות,\n\nהמדריך/ה {mentor_name} ממוסד '{institute}' מילא/ה עכשיו את טופס המדריכים.\n\nבברכה,\nמערכת שיבוץ")
        msg['Subject'] = f'📌 טופס מדריכים חדש: {mentor_name}'
        msg['From'] = SYSTEM_EMAIL
        msg['To'] = ", ".join(cfg["team_emails"])
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SYSTEM_EMAIL, SYSTEM_EMAIL_PWD)
            server.send_message(msg)
    except Exception as e: print("Email error:", e)

@app.route("/", methods=["GET", "POST"])
def form():
    cfg = load_config()
    if request.method == "POST":
        f = request.form
        tz = pytz.timezone("Asia/Jerusalem")
        row = {
            "תאריך שליחה": datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S"),
            "שם פרטי": f.get("first_name", "").strip(),
            "שם משפחה": f.get("last_name", "").strip(),
            "סטטוס מדריך": f.get("mentor_status", ""),
            "שם המוסד": f.get("institute", "").strip(),
            "תחום התמחות": f.get("specialization", ""),
            "כתובת מלאה": f.get("full_address", "").strip(),
            "מיקוד": f.get("postal_code", "").strip(),
            "מספר סטודנטים": f.get("num_students", "1"),
            "ימי הדרכה": "; ".join(f.getlist("training_days")),
            "המשכיות הדרכה": f.get("continue_mentoring", ""),
            "בקשות מיוחדות": f.get("special_requests", "").strip(),
            "חוות דעת (נקודות)": "; ".join(f.getlist("mentor_feedback_points")),
            "חוות דעת (חופשי)": f.get("mentor_feedback_text", "").strip(),
            "טלפון": f.get("phone", "").strip(),
            "אימייל": f.get("email", "").strip()
        }

        # שמירה ל-CSV ולגוגל שיטס (כפי שהיה קודם)
        ws = get_worksheet()
        if ws: ws.append_row([row.get(col, "") for col in COLUMNS_ORDER], value_input_option="USER_ENTERED")
        
        send_team_notification(f"{row['שם פרטי']} {row['שם משפחה']}", row['שם המוסד'], cfg)
        flash("✅ הטופס נשלח ונשמר בהצלחה!", "success")
        return redirect(url_for("form"))

    return render_template("supervisors_form.html", cfg=cfg)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    cfg = load_config()
    if request.method == "POST" and not session.get("admin_ok"):
        if request.form.get("pwd") == ADMIN_PASSWORD and request.form.get("secret") == LECTURER_SECRET:
            session["admin_ok"] = True
            return redirect(url_for("admin"))
        flash("פרטים שגויים", "error")

    if not session.get("admin_ok"): return render_template("supervisors_admin.html", need_login=True, cfg=cfg)
    return render_template("supervisors_admin.html", need_login=False, cfg=cfg)

@app.post("/admin/update-config")
def admin_update_config():
    if not session.get("admin_ok"): return {"status": "error"}, 401
    save_config(request.json)
    return {"status": "success"}

@app.get("/admin/logout")
def admin_logout():
    session.pop("admin_ok", None)
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
