import sqlite3
import csv
import os
from datetime import datetime

DB_PATH = "mentors_system.db"
BACKUP_FILE = "submissions_backup.csv"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # טבלת הגדרות כלליות ורשימות
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    # טבלת שדות מותאמים אישית שהמרצים יכולים להוסיף
    c.execute('''CREATE TABLE IF NOT EXISTS custom_fields (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, label TEXT, field_type TEXT, is_required INTEGER
    )''')
    # טבלת סדר תצוגת חלקי הטופס
    c.execute('''CREATE TABLE IF NOT EXISTS form_order (
        section_id TEXT PRIMARY KEY, sort_order INTEGER
    )''')
    
    # הזנת נתוני ברירת מחדל אם המסד ריק
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_password', '1234')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('specializations', 'רווחה,מוגבלות,זקנה,ילדים ונוער,בריאות הנפש,שיקום,משפחה,נשים,בריאות,קהילה')")
    
    default_order = [('personal', 1), ('institute', 2), ('address', 3), ('students', 4), ('continue', 5), ('requests', 6), ('feedback', 7), ('contact', 8), ('custom_fields', 9)]
    for sec, order in default_order:
        c.execute("INSERT OR IGNORE INTO form_order (section_id, sort_order) VALUES (?, ?)", (sec, order))
        
    conn.commit()
    conn.close()

def get_settings():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    settings = {row[0]: row[1] for row in c.fetchall()}
    
    c.execute("SELECT section_id, sort_order FROM form_order ORDER BY sort_order")
    settings['form_order'] = c.fetchall()
    
    c.execute("SELECT name, label, field_type, is_required FROM custom_fields")
    settings['custom_fields'] = c.fetchall()
    
    conn.close()
    return settings

def update_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
    conn.commit()
    conn.close()

def backup_to_csv(record_dict, columns_order):
    file_exists = os.path.isfile(BACKUP_FILE)
    with open(BACKUP_FILE, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=columns_order)
        if not file_exists:
            writer.writeheader()
        writer.writerow(record_dict)
