# -*- coding: utf-8 -*-
import csv
import json
import os
from pathlib import Path
from datetime import datetime

import pytz
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET", "devkey")

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = DATA_DIR / "config.json"
STUDENT_CSV = DATA_DIR / "student_submissions.csv"
MENTOR_CSV = DATA_DIR / "mentor_mapping_submissions.csv"

ISRAEL_TZ = pytz.timezone("Asia/Jerusalem")


DEFAULT_CONFIG = {
    "form_title": "שאלון שיבוץ סטודנטים – תשפ״ו",
    "form_subtitle": "מלאי/מלא את כל הסעיפים. השדות המסומנים ב-* הם חובה.",
    "socialAffiliations": ["דרוזי", "יהודי", "מוסלמי", "נוצרי", "אחר"],
    "languages": ["עברית", "ערבית", "אנגלית", "רוסית", "אחר"],
    "degreeTracks": [
        {"name": "תואר ראשון"},
        {"name": "תואר שני"},
        {"name": "השלמות - שנה א'"},
        {"name": "השלמות - שנה ב'"}
    ],
    "fields": [
        {"id": "welfare", "name": "מחלקות לשירותים חברתיים / רווחה", "allowedDegreeYears": []},
        {"id": "children_youth", "name": "ילדים ונוער", "allowedDegreeYears": []},
        {"id": "family", "name": "משפחה", "allowedDegreeYears": []},
        {"id": "health", "name": "בריאות", "allowedDegreeYears": []},
        {"id": "community", "name": "קהילה", "allowedDegreeYears": []}
    ],
    "trainingPlaces": [
        {"name": "מחלקה לשירותים חברתיים - אבו סנאן", "fieldIds": ["welfare"]},
        {"name": "לשכת רווחה - עכו", "fieldIds": ["welfare"]},
        {"name": "מרכז ילדים ונוער", "fieldIds": ["children_youth"]},
        {"name": "מרכז משפחה", "fieldIds": ["family"]},
        {"name": "מרכז בריאות קהילתי", "fieldIds": ["health"]},
        {"name": "מרכז קהילתי", "fieldIds": ["community"]}
    ],
    "yearRules": {
        "תואר ראשון - שנה א'": {"fields": [], "places": []},
        "תואר ראשון - שנה ב'": {"fields": ["welfare"], "places": []},
        "תואר ראשון - שנה ג'": {"fields": ["children_youth", "family", "health", "community"], "places": []},
        "תואר שני - שנה א'": {"fields": [], "places": []},
        "תואר שני - שנה ב'": {"fields": [], "places": []}
    },
    "accommodationTypes": ["אין", "רפואיות", "לימודיות", "נגישות", "אחר"],
    "mentor_statuses": ["פעיל", "לא פעיל", "חדש", "בהמתנה"],
    "feedback_points": ["זמינות להדרכה", "ניסיון מקצועי", "התאמה לסטודנטים", "הערות נוספות"]
}


def now_str():
    return datetime.now(ISRAEL_TZ).strftime("%Y-%m-%d %H:%M:%S")


def normalize_text(value):
    """החלפת 'הסבה' ב'השלמות' לפי דרישת המרצים."""
    if isinstance(value, str):
        return value.replace("הסבה", "השלמות")
    return value


def normalize_config(cfg):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}

    cfg["degreeTracks"] = [
        {"name": normalize_text(track.get("name", ""))}
        for track in cfg.get("degreeTracks", [])
        if track.get("name", "").strip()
    ]

    for field in cfg.get("fields", []):
        field["name"] = normalize_text(field.get("name", ""))
        field.setdefault("id", field["name"])
        field.setdefault("allowedDegreeYears", [])

    for place in cfg.get("trainingPlaces", []):
        place["name"] = normalize_text(place.get("name", ""))
        place.setdefault("fieldIds", [])

    cfg.setdefault("yearRules", {})
    cfg.setdefault("mentor_statuses", [])
    cfg.setdefault("feedback_points", [])

    return cfg


def load_config():
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return normalize_config(json.load(f))


def save_config(cfg):
    cfg = normalize_config(cfg)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def cfg_json(cfg):
    return json.dumps(cfg, ensure_ascii=False)


def append_csv(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    # שמירת כל השדות שנשלחו, כולל שדות דינמיים
    row = {"תאריך שליחה": now_str()}
    row.update(data)

    existing_headers = []
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            existing_headers = next(reader, [])

    headers = list(dict.fromkeys(existing_headers + list(row.keys())))

    rows = []
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    rows.append(row)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({h: r.get(h, "") for h in headers})


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def is_admin_logged_in():
    return session.get("admin_logged_in") is True


def require_admin():
    if not is_admin_logged_in():
        flash("יש להתחבר למערכת הניהול.", "error")
        return redirect(url_for("admin_login"))
    return None


@app.route("/")
def index():
    cfg = load_config()
    return render_template("student_form.html", cfg=cfg, cfg_json=cfg_json(cfg))


@app.route("/submit", methods=["POST"])
def submit_student():
    append_csv(STUDENT_CSV, dict(request.form))
    flash("הטופס נשלח בהצלחה. תודה רבה.", "success")
    return redirect(url_for("index"))


@app.route("/mentor-mapping")
def mentor_mapping():
    cfg = load_config()
    return render_template("mentor_mapping_form.html", cfg=cfg, cfg_json=cfg_json(cfg))


@app.route("/submit-mentor-mapping", methods=["POST"])
def submit_mentor_mapping():
    append_csv(MENTOR_CSV, dict(request.form))
    flash("טופס מיפוי המדריך נשלח בהצלחה.", "success")
    return redirect(url_for("mentor_mapping"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        secret_code = request.form.get("secret_code", "")

        expected_password = os.getenv("ADMIN_PASSWORD", "1234")
        expected_code = os.getenv("ADMIN_SECRET_CODE", "9999")

        if password == expected_password and secret_code == expected_code:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))

        flash("הסיסמה או הקוד הסודי אינם נכונים.", "error")

    return render_template("admin_login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("התנתקת מהמערכת.", "success")
    return redirect(url_for("admin_login"))


@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    cfg = load_config()

    if request.method == "POST":
        cfg = update_config_from_admin_form(cfg)
        save_config(cfg)
        flash("השינויים נשמרו בהצלחה.", "success")
        return redirect(url_for("admin_dashboard"))

    students = read_csv(STUDENT_CSV)
    return render_template(
        "admin_dashboard.html",
        cfg=cfg,
        cfg_json=cfg_json(cfg),
        rows=students,
        post_url=url_for("admin_dashboard"),
        page_title="פאנל מרצים - טופס סטודנטים",
        results_title="תשובות הסטודנטים",
        results_kind="students"
    )


@app.route("/mentor-admin", methods=["GET", "POST"])
def mentor_admin():
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    cfg = load_config()

    if request.method == "POST":
        cfg = update_config_from_admin_form(cfg)
        save_config(cfg)
        flash("השינויים נשמרו בהצלחה גם עבור טופס מיפוי המדריכים.", "success")
        return redirect(url_for("mentor_admin"))

    mentors = read_csv(MENTOR_CSV)
    return render_template(
        "mentor_mapping_admin.html",
        cfg=cfg,
        cfg_json=cfg_json(cfg),
        rows=mentors,
        post_url=url_for("mentor_admin"),
        page_title="פאנל מרצים - טופס מיפוי מדריכים",
        results_title="נתוני מיפוי מדריכים",
        results_kind="mentors"
    )


def parse_json_field(name, fallback):
    raw = request.form.get(name, "")
    if not raw.strip():
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def update_config_from_admin_form(cfg):
    cfg["form_title"] = request.form.get("form_title", cfg.get("form_title", ""))
    cfg["form_subtitle"] = request.form.get("form_subtitle", cfg.get("form_subtitle", ""))

    cfg["degreeTracks"] = parse_json_field("degreeTracks_json", cfg.get("degreeTracks", []))
    cfg["fields"] = parse_json_field("fields_json", cfg.get("fields", []))
    cfg["trainingPlaces"] = parse_json_field("trainingPlaces_json", cfg.get("trainingPlaces", []))
    cfg["yearRules"] = parse_json_field("yearRules_json", cfg.get("yearRules", {}))
    cfg["accommodationTypes"] = parse_json_field("accommodationTypes_json", cfg.get("accommodationTypes", []))
    cfg["mentor_statuses"] = parse_json_field("mentorStatuses_json", cfg.get("mentor_statuses", []))
    cfg["feedback_points"] = parse_json_field("feedbackPoints_json", cfg.get("feedback_points", []))

    return normalize_config(cfg)


@app.route("/download/<kind>")
def download(kind):
    redirect_response = require_admin()
    if redirect_response:
        return redirect_response

    if kind == "students":
        path = STUDENT_CSV
        filename = "student_submissions.csv"
    elif kind == "mentors":
        path = MENTOR_CSV
        filename = "mentor_mapping_submissions.csv"
    else:
        flash("סוג קובץ לא מוכר.", "error")
        return redirect(url_for("admin_dashboard"))

    if not path.exists():
        flash("עדיין אין נתונים להורדה.", "error")
        return redirect(url_for("admin_dashboard"))

    return send_file(path, as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(debug=True)
