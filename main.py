# main.py
# -*- coding: utf-8 -*-
import os
import re
import json
import csv
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session
from markupsafe import Markup
import pytz
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "dev-secret-change-me")
CONFIG_FILE = "config.json"
BACKUP_FILE = "data_backup.csv"

# פונקציות עזר לקריאה וכתיבה של הגדרות
def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

@app.before_request
def maintenance_mode():
    if os.getenv("MAINTENANCE_MODE", "0") == "1" and request.path == "/":
        html = """
        <html lang="he" dir="rtl">
        <head>
          <meta charset="utf-8">
          <title>האתר סגור</title>
          <style>
            body{font-family:system-ui; background:#f8fafc; text-align:center; padding-top:120px;}
            .box{display:inline-block; padding:32px 40px; border-radius:18px; background:#fff; box-shadow:0 10px 30px rgba(15,23,42,.08);}
          </style>
        </head>
        <body>
          <div class="box"><h1>⚙️ האתר סגור כרגע</h1><p>הגישה לטופס הוגבלה זמנית.</p></div>
        </body>
        </html>
        """
        return Markup(html), 503

# חיבור לגוגל שיטס וסנכרון עמודות
def get_worksheet():
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.environ.get("SPREADSHEET_ID")
    if not creds_json or not sheet_id:
        return None

    try:
        creds_dict = json.loads(creds_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        return gc.open_by_key(sheet_id).sheet1
    except Exception as e:
        print("Google Sheets connection error:", e)
        return None

def sync_google_sheet_headers(ws, headers):
    if not ws: return
    existing = ws.get_all_values()
    if not existing:
        ws.append_row(headers)
    elif existing[0] != headers:
        # סנכרון חכם: אם העמודות השתנו, מעדכן את השורה הראשונה
        ws.update(f'A1:{chr(65+len(headers)-1)}1', [headers])

# גיבוי מקומי 
def backup_to_csv(record_dict, headers):
    file_exists = os.path.isfile(BACKUP_FILE)
    try:
        with open(BACKUP_FILE, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if not file_exists:
                writer.writeheader()
            writer.writerow(record_dict)
    except Exception as e:
        print("CSV Backup error:", e)

# התראת אימייל לצוות
def send_team_notification(record):
    admin_email = os.environ.get("ADMIN_EMAIL")
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = os.environ.get("SMTP_PORT", 587)
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    
    if not all([admin_email, smtp_server, smtp_user, smtp_pass]):
        return
        
    msg = MIMEText(f"התקבל טופס מדריך חדש מאת {record.get('שם פרטי')} {record.get('שם משפחה')}.\nמוסד: {record.get('מוסד')}", 'plain', 'utf-8')
    msg['Subject'] = 'הגשת טופס מיפוי מדריכים חדשה'
    msg['From'] = smtp_user
    msg['To'] = admin_email

    try:
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Email notification error:", e)

@app.route("/", methods=["GET", "POST"])
def index():
    config_data = load_config()
    
    if request.method == "POST":
        f = request.form
        errors = []

        if not f.get("first_name"): errors.append("יש למלא שם פרטי.")
        if not f.get("last_name"): errors.append("יש למלא שם משפחה.")
        if not f.get("institute"): errors.append("יש למלא שם מוסד.")
        
        phone_raw = f.get("phone", "")
        phone = phone_raw.replace("-", "").replace(" ", "")
        if phone and not re.match(r"^(0?5\d{8})$", phone):
            errors.append("מספר טלפון לא תקין.")

        email = f.get("email", "").strip()
        if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors.append("כתובת דוא\"ל לא תקינה.")

        if errors:
            return json.dumps({"status": "error", "errors": errors})

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
            "מספר סטודנטים": f.get("num_students", "1"),
            "מעוניין להמשיך": f.get("continue_mentoring", "").strip(),
            "בקשות מיוחדות": f.get("special_requests", "").strip(),
            "חוות דעת - נקודות": "; ".join(f.getlist("mentor_feedback_points")),
            "חוות דעת - טקסט": f.get("mentor_feedback_text", "").strip(),
            "טלפון": phone,
            "אימייל": email
        }

        headers = list(record.keys())
        
        # שמירה ופעולות רקע
        backup_to_csv(record, headers)
        ws = get_worksheet()
        if ws:
            try:
                sync_google_sheet_headers(ws, headers)
                ws.append_row(list(record.values()))
            except Exception as e:
                print("Sheets append error:", e)
        
        send_team_notification(record)
        return json.dumps({"status": "success", "message": "✅ הטופס נשלח ונשמר בהצלחה! תודה 🌟"})

    return render_template("supervisor_form.html", config=config_data)

# פאנל ניהול
@app.route("/admin", methods=["GET", "POST"])
def admin():
    config_data = load_config()
    
    if "admin_logged_in" not in session:
        if request.method == "POST":
            pwd = request.form.get("password")
            if pwd == config_data.get("admin_password"):
                session["admin_logged_in"] = True
                return redirect(url_for("admin"))
            else:
                flash("סיסמה שגויה.", "error")
        return render_template("admin_login.html")

    if request.method == "POST" and request.form.get("action") == "save_config":
        new_specs = [s.strip() for s in request.form.get("specializations", "").split("\n") if s.strip()]
        new_statuses = [s.strip() for s in request.form.get("mentor_statuses", "").split("\n") if s.strip()]
        new_order = request.form.get("section_order", "").split(",")
        
        config_data["specializations"] = new_specs
        config_data["mentor_statuses"] = new_statuses
        if new_order and len(new_order) >= 8:
            config_data["section_order"] = new_order
            
        save_config(config_data)
        flash("ההגדרות נשמרו בהצלחה!", "success")
        return redirect(url_for("admin"))

    return render_template("admin_dashboard.html", config=config_data)

@app.route("/admin/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
