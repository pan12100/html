import os
from google.oauth2.service_account import Credentials
import gspread

scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]

creds_path = os.getenv("GOOGLE_CREDS")  # ต้องเป็น path ของไฟล์ JSON จริง
if not creds_path:
    print("⚠️ GOOGLE_CREDS environment variable is missing!")
else:
    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=scope)
        client = gspread.authorize(creds)
        sheet_users = client.open("BMI_system").worksheet("users")
        sheet_bmi = client.open("BMI_system").worksheet("bmi_data")
        print("✅ เข้าถึง Google Sheets ได้")
    except Exception as e:
        print(f"❌ Failed to access Google Sheets: {e}")
