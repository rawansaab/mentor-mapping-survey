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

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials
from gspread_formatting import CellFormat, Color, TextFormat, format_cell_range

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET", "super-secret-key")

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / "supervisors_config.json"
CSV_FILE = DATA_DIR / "supervisors_data.csv"

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "rawan_0304")
LECTURER_SECRET = os.getenv("LECTURER_SECRET", "secret_2026")
SYSTEM_EMAIL = os.getenv("ADMIN_EMAIL", "") # המייל של המערכת שישלח את ההתראות
SYSTEM_EMAIL_PWD = os.getenv("MAIL_PASSWORD", "") 

# תצורת ברירת מחדל
DEFAULT_CONFIG = {
    "form_title": "📋 מיפוי מדריכים לשיבוץ סטודנטים - תשפ\"ו",
    "form_subtitle": "מטרת טופס זה היא לאסוף מידע עדכני על מדריכים ומוסדות לקראת שנת ההכשרה הקרובה.",
    "mentor_statuses": ["מדריך חדש (נדרש קורס)", "מדריך ותיק", "רכז/ת"],
    "specializations": ["רווחה", "מוגבלות", "זקנה", "ילדים ונוער בסיכון", "בריאות הנפש", "שיקום", "משפחה", "נשים", "בריאות", "קהילה"],
    "feedback_points": ["זמינות גבוהה", "ליווי מקצועי משמעותי", "שיתוף פעולה עם המוסד", "צורך בחיזוק בליווי"],
    "training_days": ["ראשון", "שני", "שלישי", "רביעי", "חמישי"],
    "team_emails": [], # רשימת המיילים של הצוות שיקבלו התראות
    "section_order": ["personal", "institution", "capacity", "feedback", "contact"] # הסדר שהמרצים יכולים לשנות
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
    "כתובת מלאה (רחוב ועיר)", "מיקוד", "מספר סטודנטים לקליטה", "ימי הדרכה אפשריים",
    "המשכיות הדרכה", "בקשות מיוחדות", "חוות דעת (נקודות)", "חוות דעת (חופשי)", "טלפון", "אימייל"
]

def get_worksheet():
    gc_info_env = os.getenv("GOOGLE_CREDENTIALS")
    if not gc_info_env: return None
    creds = Credentials.from_service_account_info(json.loads(gc_info_env), scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(os.getenv("SUPERVISORS_SPREADSHEET_ID")) # שימי לב: ID נפרד לטופס מדריכים!
    return sh.sheet1

def send_team_notification(mentor_name, institute, cfg):
    """ שולחת מייל אוטומטי לצוות ברגע שמדריך מסיים """
    if not SYSTEM_EMAIL or not SYSTEM_EMAIL_PWD or not cfg.get("team_emails"): return
    
    try:
        msg = EmailMessage()
        msg.set_content(f"שלום לצוות,\n\nהמדריך/ה {mentor_name} ממוסד '{institute}' מילא/ה עכשיו את טופס מיפוי המדריכים.\nהנתונים עודכנו בהצלחה בגיליון.\n\nבברכה,\nמערכת שיבוץ אוטומטית")
        msg['Subject'] = f'📌 טופס מדריכים חדש התקבל: {mentor_name}'
        msg['From'] = SYSTEM_EMAIL
        msg['To'] = ", ".join(cfg["team_emails"])

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SYSTEM_EMAIL, SYSTEM_EMAIL_PWD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Error sending email:", e)

# ================= PUBLIC FORM =================
@app.route("/", methods=["GET", "POST"])
def form():
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
            return redirect(url_for("form"))

        # שמירת נתונים
        tz = pytz.timezone("Asia/Jerusalem")
        row = {
            "תאריך שליחה": datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S"),
            "שם פרטי": f.get("first_name", "").strip(),
            "שם משפחה": f.get("last_name", "").strip(),
            "סטטוס מדריך": f.get("mentor_status", ""),
            "שם המוסד": f.get("institute", "").strip(),
            "תחום התמחות": f.get("specialization", ""),
            "כתובת מלאה (רחוב ועיר)": f.get("full_address", "").strip(),
            "מיקוד": f.get("postal_code", "").strip(),
            "מספר סטודנטים לקליטה": f.get("num_students", "1"),
            "ימי הדרכה אפשריים": "; ".join(f.getlist("training_days")),
            "המשכיות הדרכה": f.get("continue_mentoring", ""),
            "בקשות מיוחדות": f.get("special_requests", "").strip(),
            "חוות דעת (נקודות)": "; ".join(f.getlist("mentor_feedback_points")),
            "חוות דעת (חופשי)": f.get("mentor_feedback_text", "").strip(),
            "טלפון": phone,
            "אימייל": email
        }

        # שמירה ל-CSV
        df_new = pd.DataFrame([row])
        if CSV_FILE.exists():
            df_master = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
            df_master = pd.concat([df_master, df_new], ignore_index=True)
        else:
            df_master = df_new
        
        for c in COLUMNS_ORDER:
            if c not in df_master.columns: df_master[c] = ""
        df_master[COLUMNS_ORDER].to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

        # שמירה לגוגל שיטס
        ws = get_worksheet()
        if ws:
            headers = ws.row_values(1)
            if not headers or headers != COLUMNS_ORDER:
                cell_list = ws.range(1, 1, 1, len(COLUMNS_ORDER))
                for i, cell in enumerate(cell_list): cell.value = COLUMNS_ORDER[i]
                ws.update_cells(cell_list)
                format_cell_range(ws, "1:1", CellFormat(backgroundColor=Color(0.2, 0.6, 0.4), textFormat=TextFormat(bold=True, foregroundColor=Color(1,1,1))))
            ws.append_row([row.get(col, "") for col in COLUMNS_ORDER], value_input_option="USER_ENTERED")

        # שליחת מייל לצוות!
        send_team_notification(f"{row['שם פרטי']} {row['שם משפחה']}", row['שם המוסד'], cfg)

        flash("✅ הטופס נשלח ונשמר בהצלחה! תודה רבה.", "success")
        return redirect(url_for("form"))

    return render_template("supervisors_form.html", cfg=cfg)

# ================= ADMIN PANEL =================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    cfg = load_config()
    
    if request.method == "POST":
        pwd, secret = request.form.get("pwd", ""), request.form.get("secret", "")
        if pwd == ADMIN_PASSWORD and secret == LECTURER_SECRET:
            session["admin_ok"] = True
            return redirect(url_for("admin"))
        flash("סיסמה או קוד סודי שגויים", "error")
        return redirect(url_for("admin"))

    if not session.get("admin_ok"):
        return render_template("supervisors_admin.html", need_login=True, cfg=cfg)

    mentors_data = pd.read_csv(CSV_FILE, encoding="utf-8-sig").to_dict("records") if CSV_FILE.exists() else []
    return render_template("supervisors_admin.html", need_login=False, cfg=cfg, mentors=mentors_data)

@app.post("/admin/update-config")
def admin_update_config():
    if not session.get("admin_ok"): return {"status": "error"}, 401
    try:
        new_cfg = request.json
        current_cfg = load_config()
        current_cfg.update(new_cfg)
        save_config(current_cfg)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

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
    flash("אין עדיין נתונים להורדה", "error")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
