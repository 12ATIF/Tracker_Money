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

    print("\nReading ALL Categories:")
    result = mgr.sheet.values().get(
        spreadsheetId=SHEET_ID,
        range='Categories!A2:F', 
    ).execute()
    rows = result.get('values', [])
    for row in rows:
        # ID, Name, Type, Icon, Limit, Keywords
        if len(row) >= 6:
            print(f"Cat: {row[1]} | Keywords: {row[5]}")

    print("\nReading Transactions sheet first 5 rows (to check existing categories):")
    result = mgr.sheet.values().get(
        spreadsheetId=SHEET_ID,
        range='Transactions!A1:F5', 
    ).execute()
    rows = result.get('values', [])
    for row in rows:
        print(row)
        
except Exception as e:
    print(f"❌ Error: {e}")
