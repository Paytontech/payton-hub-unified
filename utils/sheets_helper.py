import gspread
import pandas as pd
import requests
import io
import os
import json
import time
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

class SheetsHelper:
    def __init__(self):
        self.spreadsheet_id = os.getenv("SPREADSHEET_ID")
        self.credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        self._gc = None
        self._cache = {}
        self._cache_expiry = 60 # 1 minute cache

    def _get_client(self):
        if self._gc: return self._gc
        
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # Try from environment variable first (JSON string)
        if self.credentials_json:
            try:
                creds_dict = json.loads(self.credentials_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                self._gc = gspread.authorize(creds)
                return self._gc
            except Exception as e:
                print(f"Sheets Auth Error (Env): {e}")

        # Fallback to local file
        creds_path = os.path.join(os.path.dirname(__file__), "..", "google_credentials.json")
        if os.path.exists(creds_path):
            try:
                creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
                self._gc = gspread.authorize(creds)
                return self._gc
            except Exception as e:
                print(f"Sheets Auth Error (File): {e}")
                
        return None

    def get_sheet_data(self, sheet_name, bypass_cache=False):
        now = time.time()
        if not bypass_cache and sheet_name in self._cache:
            data, expiry = self._cache[sheet_name]
            if now < expiry:
                return data

        client = self._get_client()
        if client:
            try:
                sh = client.open_by_key(self.spreadsheet_id)
                worksheet = sh.worksheet(sheet_name)
                data = worksheet.get_all_records()
                self._cache[sheet_name] = (data, now + self._cache_expiry)
                return data
            except Exception as e:
                print(f"Error reading {sheet_name} via API: {e}")
        
        # Fallback to public CSV (only if not authenticated)
        url = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text))
                data = df.to_dict(orient='records')
                # Cache CSV results too but shorter
                self._cache[sheet_name] = (data, now + 30) 
                return data
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
            self._cache.pop(sheet_name, None) # Clear cache
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
            self._cache.pop(sheet_name, None) # Clear cache
            return True
        except Exception as e:
            print(f"Error updating {sheet_name}: {e}")
            return False
