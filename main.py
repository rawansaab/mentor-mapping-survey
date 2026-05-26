# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
import pytz

from db_manager import init_db, get_settings, update_setting, backup_to_csv
from sheets_sync import get_worksheet, sync_google_sheet_headers

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "dev-secret-change-me")

init_db()

BASE_COLUMNS = [
    "תאריך שליחה", "שם פרטי", "שם משפחה", "סטטוס מדריך", "מוסד", "תחום התמחות",
    "רחוב", "עיר", "מיקוד", "מספר סטודנטים שניתן לקלוט (1 או 2)",
    "מעוניין להמשיך", "בקשות מיוחדות", "חוות דעת - נקודות",
    "חוות דעת - טקסט חופשי", "טלפון", "אימייל"
]

@app.route("/", methods=["GET", "POST"])
def index():
    settings = get_settings()
    specializations = settings.get('specializations', '').split(',')
    
    if request.method == "POST":
        f = request.form
        tz = pytz.timezone("Asia/Jerusalem")
        
        # בניית הרשומה הבסיסית
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
            "מספר סטודנטים שניתן לקלוט (1 או 2)": f.get("num_students", "1"),
            "מעוניין להמשיך": f.get("continue_mentoring", "").strip(),
            "בקשות מיוחדות": f.get("special_requests", "").strip(),
            "חוות דעת - נקודות": "; ".join(f.getlist("mentor_feedback_points")),
            "חוות דעת - טקסט חופשי": f.get("mentor_feedback_text", "").strip(),
            "טלפון": f.get("phone", "").replace("-", "").replace(" ", ""),
            "אימייל": f.get("email", "").strip()
        }

        # איסוף שדות דינמיים שהמרצים הוסיפו
        dynamic_columns = list(BASE_COLUMNS)
        for cf in settings['custom_fields']:
            field_name = cf[0]
            record[field_name] = f.get(field_name, "").strip()
            dynamic_columns.append(field_name)

        try:
            # עדכון עמודות וגיבויים
            ws = get_worksheet()
            final_headers = sync_google_sheet_headers(ws, dynamic_columns)
            row_data = [record.get(col, "") for col in final_headers]
            ws.append_row(row_data)
            backup_to_csv(record, final_headers)
            
            flash("✅ הטופס נשלח ונשמר בהצלחה! תודה 🌟", "success")
        except Exception as e:
            import traceback
            print("Error saving:", e)
            traceback.print_exc()
            flash(f"❌ שגיאה בשמירה לגיליון: {e}", "error")

        return redirect(url_for("index"))

    return render_template("mentor_form.html", specializations=specializations, settings=settings)

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    settings = get_settings()
    if request.method == "POST":
        if request.form.get('password') == settings.get('admin_password'):
            session['admin_logged_in'] = True
            flash("התחברת בהצלחה לפאנל המרצים.", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("סיסמה שגויה, נסה שוב.", "error")
            
    return render_template("admin_login.html")

@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    settings = get_settings()
    
    if request.method == "POST":
        if 'update_specs' in request.form:
            update_setting('specializations', request.form.get('specializations_text', ''))
            flash("✅ תחומי ההתמחות עודכנו בהצלחה.", "success")
            
        return redirect(url_for('admin_dashboard'))

    return render_template("admin_dashboard.html", settings=settings)

@app.route("/logout")
def logout():
    session.pop('admin_logged_in', None)
    flash("התנתקת מהמערכת.", "success")
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
