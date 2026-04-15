import os
import json
from datetime import datetime, timezone


class SheetsLogger:
    RANGES = {
        "x":        "X_Log!A:F",
        "medium":   "Medium_Log!A:F",
        "tiktok":   "TikTok_Log!A:F",
        "youtube":  "YouTube_Log!A:F",
        "instagram":"Instagram_Log!A:F",
    }

    def __init__(self):
        creds_json = os.environ.get("GOOGLE_SHEETS_CREDS", "")
        self.sid   = os.environ.get("SPREADSHEET_ID", "")
        self.svc   = None

        if creds_json and self.sid:
            try:
                from google.oauth2.service_account import Credentials
                from googleapiclient.discovery import build
                creds = Credentials.from_service_account_info(
                    json.loads(creds_json),
                    scopes=["https://www.googleapis.com/auth/spreadsheets"],
                )
                self.svc = build("sheets", "v4", credentials=creds)
            except Exception as e:
                print(f"  ⚠️  SheetsLogger init failed: {e}")

    def log_success(self, platform: str, niche: str, product: dict, result: str):
        self._append(platform, [
            datetime.now(timezone.utc).isoformat(),
            platform, niche,
            product.get("product", ""),
            "SUCCESS", str(result),
        ])

    def log_error(self, platform: str, niche: str, product: dict, error: str):
        pname = product.get("product", "") if isinstance(product, dict) else str(product)
        self._append(platform, [
            datetime.now(timezone.utc).isoformat(),
            platform, niche, pname, "ERROR", error,
        ])

    def _append(self, platform: str, row: list):
        if not self.svc:
            print(f"  [Sheets] {row}")
            return
        try:
            self.svc.spreadsheets().values().append(
                spreadsheetId=self.sid,
                range=self.RANGES.get(platform, "Log!A:F"),
                valueInputOption="USER_ENTERED",
                body={"values": [row]},
            ).execute()
        except Exception as e:
            print(f"  ⚠️  Sheets log failed: {e}")
