from google_sheets_handler import SheetsManager
import os
from dotenv import load_dotenv

# Hardcoded for debugging
SHEET_ID = '1LZzorEsJ62yXOtZUhAGXo7Cmk6zUbmuKY4YLYLuv_4k'

if not SHEET_ID:
    print("❌ No SHEET_ID found in .env")
    exit()

print(f"Checking Spreadsheet ID: {SHEET_ID}")

try:
    mgr = SheetsManager(SHEET_ID)
    # Get spreadsheet metadata
    spreadsheet = mgr.service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    
    print("\nSHEETS FOUND:")
    for sheet in spreadsheet.get('sheets', []):
        props = sheet['properties']
        title = props['title']
        print(f"- '{title}'")

    print("\nReading last 5 rows of Transactions:")
    result = mgr.sheet.values().get(
        spreadsheetId=SHEET_ID,
        range='Transactions!A1:I', # Read all to find last
    ).execute()
    rows = result.get('values', [])
    print(f"Total rows found: {len(rows)}")
    for row in rows[-5:]:
        print(row)
        
except Exception as e:
    print(f"❌ Error: {e}")
