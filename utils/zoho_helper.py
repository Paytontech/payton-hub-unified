import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

class ZohoHelper:
    def __init__(self):
        self.client_id = os.getenv("ZOHO_CLIENT_ID")
        self.client_secret = os.getenv("ZOHO_CLIENT_SECRET")
        self.refresh_token = os.getenv("ZOHO_REFRESH_TOKEN")
        self.api_base = "https://workdrive.zoho.in/api/v1"
        self.auth_url = "https://accounts.zoho.in/oauth/v2/token"
        self._access_token = None
        self._token_expiry = 0

    def get_access_token(self):
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token

        params = {
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token"
        }
        try:
            response = requests.post(self.auth_url, params=params)
            data = response.json()
            if "access_token" in data:
                self._access_token = data["access_token"]
                self._token_expiry = time.time() + 3500
                return self._access_token
            else:
                return None
        except Exception as e:
            print(f"Zoho Auth Error: {e}")
            return None

    def get_or_create_folder(self, parent_id, folder_name):
        token = self.get_access_token()
        if not token: return None
        headers = { "Authorization": f"Zoho-oauthtoken {token}", "Accept": "application/vnd.api+json" }
        list_url = f"{self.api_base}/files/{parent_id}/files"
        try:
            response = requests.get(list_url, headers=headers)
            if response.status_code == 200:
                files = response.json().get("data", [])
                for f in files:
                    if f["attributes"]["name"] == folder_name and f["attributes"]["is_folder"]:
                        return f["id"]
            
            payload = { "data": { "attributes": { "name": folder_name, "parent_id": parent_id }, "type": "files" } }
            create_res = requests.post(f"{self.api_base}/files", headers=headers, json=payload)
            return create_res.json().get("data", {}).get("id")
        except Exception as e:
            print(f"Zoho Folder Error: {e}")
            return None

    def upload_file(self, folder_id, file_content, filename):
        token = self.get_access_token()
        if not token: return None
        url = f"https://workdrive.zoho.in/api/v1/upload"
        params = { "parent_id": folder_id, "filename": filename, "override-name-exist": "true" }
        headers = { "Authorization": f"Zoho-oauthtoken {token}", "Accept": "application/vnd.api+json" }
        files = { "content": (filename, file_content) }
        try:
            response = requests.post(url, headers=headers, params=params, files=files)
            data = response.json()
            if "data" in data:
                return data["data"][0]["attributes"]["Permalink"]
            return None
        except Exception as e:
            print(f"Zoho Upload Error: {e}")
            return None
