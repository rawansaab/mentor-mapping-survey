import os
import ast
import gspread
from google.oauth2.service_account import Credentials

def get_worksheet():
    # קבלת המילון כטקסט והמרתו למילון פייתון תקני ללא שימוש ב-import json
    creds_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_DICT")
    sheet_id = os.environ.get("SPREADSHEET_ID")
    
    if not creds_str or not sheet_id:
        raise RuntimeError("Missing Google Sheets environment variables.")
        
    creds_dict = ast.literal_eval(creds_str) # ממיר מחרוזת מילון לאובייקט מילון
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    return gc.open_by_key(sheet_id).sheet1

def sync_google_sheet_headers(ws, required_columns):
    existing = ws.get_all_values()
    if not existing:
        ws.append_row(required_columns)
        return required_columns
        
    current_headers = existing[0]
    updates = False
    
    # בודק אם התווספו שדות מותאמים אישית שאין להם עמודה
    for col in required_columns:
        if col not in current_headers:
            current_headers.append(col)
            updates = True
            
    if updates:
        ws.update(values=[current_headers], range_name='A1')
        
    return current_headers
