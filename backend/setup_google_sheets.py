"""
CLI Setup Utility: Automatically provision and format Google Sheets for BJBWA
Run: python setup_google_sheets.py --credentials path/to/service_account.json
"""

import sys
import os
import json
import argparse
import gspread
from google.oauth2.service_account import Credentials
from billing_core import COMMERCIAL_COLUMNS, DOMESTIC_COLUMNS

SPREADSHEET_TITLE = "Basant Jamini Bhawan Maintenance Ledger"
SHEET_COMMERCIAL = "Maintenance bill"
SHEET_DOMESTIC = "Domestic Maintenance bill"

def setup_google_sheets(credentials_file, share_with_email=None, existing_sheet_id=None):
    if not os.path.exists(credentials_file):
        print(f"❌ Error: Credentials file '{credentials_file}' not found.")
        return False

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    try:
        creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        client = gspread.authorize(creds)
        print("✅ Authenticated successfully with Google Cloud.")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False

    spreadsheet = None
    if existing_sheet_id:
        try:
            spreadsheet = client.open_by_key(existing_sheet_id)
            print(f"✅ Found existing spreadsheet: '{spreadsheet.title}'")
        except Exception as e:
            print(f"❌ Could not open spreadsheet with ID '{existing_sheet_id}': {e}")
            return False
    else:
        try:
            spreadsheet = client.create(SPREADSHEET_TITLE)
            print(f"🎉 Created new Google Spreadsheet: '{SPREADSHEET_TITLE}'")
        except Exception as e:
            print(f"❌ Failed to create spreadsheet: {e}")
            return False

    if share_with_email:
        try:
            spreadsheet.share(share_with_email, perm_type='user', role='writer')
            print(f"✅ Shared spreadsheet with: {share_with_email}")
        except Exception as e:
            print(f"⚠️ Warning: Could not share spreadsheet with {share_with_email}: {e}")

    # Ensure sheets exist and format headers
    sheets_info = [
        (SHEET_COMMERCIAL, COMMERCIAL_COLUMNS),
        (SHEET_DOMESTIC, DOMESTIC_COLUMNS)
    ]

    for title, columns in sheets_info:
        try:
            ws = spreadsheet.worksheet(title)
        except Exception:
            ws = spreadsheet.add_worksheet(title=title, rows=200, cols=len(columns))

        # Write header row
        ws.update('A1', [columns])

        # Style header row (Deep Royal Blue background, white bold text)
        try:
            ws.format("1:1", {
                "backgroundColor": {"red": 0.118, "green": 0.227, "blue": 0.541},  # #1e3a8a
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10},
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE"
            })
        except Exception:
            pass

        print(f"✅ Configured and formatted sheet: '{title}' ({len(columns)} columns)")

    # Delete default 'Sheet1' if present and other sheets exist
    try:
        sheet1 = spreadsheet.worksheet("Sheet1")
        if len(spreadsheet.worksheets()) > 1:
            spreadsheet.del_worksheet(sheet1)
    except Exception:
        pass

    # Save to config file
    config_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "google_sheets_config.json")

    config_data = {
        "spreadsheet_id": spreadsheet.id,
        "spreadsheet_url": spreadsheet.url,
        "credentials_file": os.path.basename(credentials_file),
        "use_live_google_sheets": True
    }

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)

    print("\n" + "="*70)
    print("🚀 GOOGLE SHEETS SETUP COMPLETE!")
    print(f"📄 Spreadsheet ID:  {spreadsheet.id}")
    print(f"🔗 Spreadsheet URL: {spreadsheet.url}")
    print(f"⚙️ Configuration saved to: {config_file}")
    print("="*70)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Google Sheets for BJBWA Billing Hub")
    parser.add_argument("--credentials", default="service_account.json", help="Path to Google Service Account JSON file")
    parser.add_argument("--share", help="Email address to share the spreadsheet with")
    parser.add_argument("--id", help="Existing spreadsheet ID to configure instead of creating a new one")
    args = parser.parse_args()

    setup_google_sheets(args.credentials, args.share, args.id)
