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
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET", "dev-secret-change-me")

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
    "specializations": ["רווחה", "מוגבלות", "זקנה", "ילדים ונוער", "בריאות הנפש", "שיקום", "משפחה", "נשים", "בריאות", "קהילה"],
    "feedback_options": ["זמינות גבוהה", "ליווי מקצועי משמעותי", "שיתוף פעולה עם המוסד", "צורך בחיזוק בליווי"],
    "team_emails": []
}

def load_config():
    if CONFIG_FILE.exists():
        try: return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except: return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

COLUMNS_ORDER = [
    "תאריך שליחה", "שם פרטי", "שם משפחה", "סטטוס מדריך", "מוסד", "תחום התמחות",
    "רחוב", "עיר", "מיקוד", "מספר סטודנטים שניתן לקלוט (1 או 2)",
    "מעוניין להמשיך", "בקשות מיוחדות", "חוות דעת - נקודות",
    "חוות דעת - טקסט חופשי", "טלפון", "אימייל"
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
        msg['Subject'] = f'📌 טופס מדריכים חדש התקבל: {mentor_name}'
        msg['From'] = SYSTEM_EMAIL
        msg['To'] = ", ".join(cfg["team_emails"])
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SYSTEM_EMAIL, SYSTEM_EMAIL_PWD)
            server.send_message(msg)
    except Exception as e: print("Email error:", e)

@app.route("/", methods=["GET", "POST"])
def index():
    cfg = load_config()
    if request.method == "POST":
        f = request.form
        errors = []

        phone = f.get("phone", "").replace("-", "").replace(" ", "")
        email = f.get("email", "").strip()

        if not f.get("first_name"): errors.append("יש למלא שם פרטי.")
        if not f.get("institute"): errors.append("יש למלא שם מוסד.")
        if not re.match(r"^(0?5\d{8})$", phone): errors.append("מספר טלפון לא תקין.")
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email): errors.append("כתובת דוא\"ל לא תקינה.")

        if errors:
            for e in errors: flash(e, "error")
            return redirect(url_for("index"))

        tz = pytz.timezone("Asia/Jerusalem")
        record = {
            "תאריך שליחה": datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
            "שם פרטי": f.get("first_name", "").strip(),
            "שם משפחה": f.get("last_name", "").strip(),
            "סטטוס מדריך": f.get("mentor_status", ""),
            "מוסד": f.get("institute", "").strip(),
            "תחום התמחות": f.get("specialization", ""),
            "רחוב": f.get("street", "").strip(),
            "עיר": f.get("city", "").strip(),
            "מיקוד": f.get("postal_code", "").strip(),
            "מספר סטודנטים שניתן לקלוט (1 או 2)": f.get("num_students", "1"),
            "מעוניין להמשיך": f.get("continue_mentoring", ""),
            "בקשות מיוחדות": f.get("special_requests", "").strip(),
            "חוות דעת - נקודות": "; ".join(f.getlist("mentor_feedback_points")),
            "חוות דעת - טקסט חופשי": f.get("mentor_feedback_text", "").strip(),
            "טלפון": phone,
            "אימייל": email
        }

        # שמירה לגוגל שיטס
        ws = get_worksheet()
        if ws:
            ws.append_row([record.get(col, "") for col in COLUMNS_ORDER], value_input_option="USER_ENTERED")
        
        # שמירה מקבילה ל-CSV המקומי
        df_new = pd.DataFrame([record])
        if CSV_FILE.exists():
            df_master = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
            df_master = pd.concat([df_master, df_new], ignore_index=True)
        else:
            df_master = df_new
        df_master.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

        send_team_notification(f"{record['שם פרטי']} {record['שם משפחה']}", record['מוסד'], cfg)
        flash("✅ הטופס נשלח ונשמר בהצלחה! תודה 🌟", "success")
        return redirect(url_for("index"))

    return render_template("index.html", cfg=cfg)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    cfg = load_config()
    if request.method == "POST" and not session.get("admin_ok"):
        if request.form.get("pwd") == ADMIN_PASSWORD and request.form.get("secret") == LECTURER_SECRET:
            session["admin_ok"] = True
            return redirect(url_for("admin"))
        flash("פרטים שגויים", "error")

    if not session.get("admin_ok"): return render_template("supervisors_admin.html", need_login=True, cfg=cfg)
    mentors_data = pd.read_csv(CSV_FILE, encoding="utf-8-sig").to_dict("records") if CSV_FILE.exists() else []
    return render_template("supervisors_admin.html", need_login=False, cfg=cfg, mentors=mentors_data)

@app.post("/admin/update-config")
def admin_update_config():
    if not session.get("admin_ok"): return {"status": "error"}, 401
    save_config(request.json)
    return {"status": "success"}

@app.get("/admin/logout")
def admin_logout():
    session.pop("admin_ok", None)
    return redirect(url_for("admin"))

@app.get("/download/master")
def download_master():
    if not session.get("admin_ok"): return redirect(url_for("admin"))
    if CSV_FILE.exists():
        df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
        data = BytesIO()
        with pd.ExcelWriter(data, engine="xlsxwriter") as w: df.to_excel(w, index=False)
        data.seek(0)
        return send_file(data, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="נתוני_מדריכים.xlsx")
    flash("אין נתונים להורדה", "error")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
