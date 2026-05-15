import gspread
import pandas as pd
import requests
import io
import os
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

class SheetsHelper:
    def __init__(self):
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID")
        self.credentials_path = os.path.join(os.path.dirname(__file__), "..", "google_credentials.json")
        self._gc = None

    def _get_client(self):
        if self._gc: return self._gc
        if os.path.exists(self.credentials_path):
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            try:
                creds = Credentials.from_service_account_file(self.credentials_path, scopes=scopes)
                self._gc = gspread.authorize(creds)
                return self._gc
            except Exception as e:
                print(f"Sheets Auth Error: {e}")
        return None

    def get_sheet_data(self, sheet_name):
        client = self._get_client()
        if client:
            try:
                sh = client.open_by_key(self.spreadsheet_id)
                worksheet = sh.worksheet(sheet_name)
                return worksheet.get_all_records()
            except Exception as e:
                print(f"Error reading {sheet_name} via API: {e}")
        
        # Fallback to public CSV
        url = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text))
                return df.to_dict(orient='records')
        except Exception as e:
            print(f"Error reading {sheet_name} via CSV: {e}")
        return []

    def append_row(self, sheet_name, row_data):
        client = self._get_client()
        if not client: return False
        try:
            sh = client.open_by_key(self.spreadsheet_id)
            worksheet = sh.worksheet(sheet_name)
            worksheet.append_row(row_data)
            return True
        except Exception as e:
            print(f"Error appending to {sheet_name}: {e}")
            return False

    def update_cell(self, sheet_name, row, col, value):
        client = self._get_client()
        if not client: return False
        try:
            sh = client.open_by_key(self.spreadsheet_id)
            worksheet = sh.worksheet(sheet_name)
            worksheet.update_cell(row, col, value)
            return True
        except Exception as e:
            print(f"Error updating {sheet_name}: {e}")
            return False
