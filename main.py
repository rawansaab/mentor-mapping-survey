# (חלקי הקוד העליונים ב-main.py נשארים אותו דבר, להחליף רק את הפונקציות:)

@app.route("/", methods=["GET", "POST"])
def index():
    settings = get_settings()
    # שליפת הרשימות הדינמיות
    specializations = [s.strip() for s in settings.get('specializations', '').split(',') if s.strip()]
    mentor_statuses = [s.strip() for s in settings.get('mentor_statuses', '').split(',') if s.strip()]
    feedback_points = [s.strip() for s in settings.get('feedback_points', '').split(',') if s.strip()]
    
    if request.method == "POST":
        f = request.form
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
            "מספר סטודנטים שניתן לקלוט (1 או 2)": f.get("num_students", "1"),
            "מעוניין להמשיך": f.get("continue_mentoring", "").strip(),
            "בקשות מיוחדות": f.get("special_requests", "").strip(),
            "חוות דעת - נקודות": "; ".join(f.getlist("mentor_feedback_points")),
            "חוות דעת - טקסט חופשי": f.get("mentor_feedback_text", "").strip(),
            "טלפון": f.get("phone", "").replace("-", "").replace(" ", ""),
            "אימייל": f.get("email", "").strip()
        }

        dynamic_columns = list(BASE_COLUMNS)
        for cf in settings.get('custom_fields', []):
            field_name = cf[0]
            record[field_name] = f.get(field_name, "").strip()
            dynamic_columns.append(field_name)

        try:
            ws = get_worksheet()
            final_headers = sync_google_sheet_headers(ws, dynamic_columns)
            row_data = [record.get(col, "") for col in final_headers]
            ws.append_row(row_data)
            backup_to_csv(record, final_headers)
            flash("✅ הטופס נשלח ונשמר בהצלחה! תודה 🌟", "success")
        except Exception as e:
            flash(f"❌ שגיאה בשמירה לגיליון: {e}", "error")

        return redirect(url_for("index"))

    return render_template("mentor_form.html", 
                           settings=settings,
                           specializations=specializations,
                           mentor_statuses=mentor_statuses,
                           feedback_points=feedback_points)

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    settings = get_settings()
    if request.method == "POST":
        pwd = request.form.get('password')
        code = request.form.get('secret_code')
        if pwd == settings.get('admin_password', '1234') and code == settings.get('secret_code', '0000'):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("❌ סיסמה או קוד סודי שגויים, נסה שוב.", "error")
            
    return render_template("admin_login.html")

@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    settings = get_settings()
    
    if request.method == "POST":
        update_setting('form_title', request.form.get('form_title', ''))
        update_setting('form_subtitle', request.form.get('form_subtitle', ''))
        update_setting('specializations', request.form.get('specializations', ''))
        update_setting('mentor_statuses', request.form.get('mentor_statuses', ''))
        update_setting('feedback_points', request.form.get('feedback_points', ''))
        flash("✅ השינויים נשמרו בהצלחה.", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template("admin_dashboard.html", settings=settings)

@app.route("/logout")
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))
