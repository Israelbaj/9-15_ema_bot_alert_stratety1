# sheets_logger.py
import os
import json
from datetime import datetime
import gspread
from google.oauth2 import service_account

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

def append_to_google_sheets(record: dict):
    """
    Append a record (dict) to Google Sheets.
    Requires GOOGLE_SERVICE_ACCOUNT_JSON + GOOGLE_SHEET_ID in environment.
    """
    try:
        if not SHEET_ID or not SERVICE_JSON:
            print("⚠️ Google Sheets credentials not set, skipping cloud log.")
            return False

        creds_dict = json.loads(SERVICE_JSON)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1  # default first sheet

        # Preserve consistent column order
        row = [record.get(k, "") for k in record.keys()]
        sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"☁️ Synced {record['symbol']} → Google Sheet")

        return True

    except Exception as e:
        print(f"[ERROR] Google Sheets sync failed: {repr(e)}")
        return False
