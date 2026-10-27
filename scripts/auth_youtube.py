"""
One-time interactive browser OAuth tool to authenticate with YouTube Data API v3
and generate storage/secrets/youtube_token.json
"""

import os
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

BASE_DIR = Path(__file__).resolve().parent.parent
SECRETS_DIR = BASE_DIR / "storage" / "secrets"
SECRETS_DIR.mkdir(parents=True, exist_ok=True)

CLIENT_SECRET_FILE = SECRETS_DIR / "youtube_client_secret.json"
TOKEN_FILE = SECRETS_DIR / "youtube_token.json"


def authenticate():
    if not CLIENT_SECRET_FILE.exists():
        print(f"Error: {CLIENT_SECRET_FILE} not found!")
        print("Please download your OAuth client secret JSON from Google Cloud Console")
        print(f"and place it at: {CLIENT_SECRET_FILE}")
        sys.exit(1)

    print(f"Starting OAuth flow using: {CLIENT_SECRET_FILE}")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
    creds = flow.run_local_server(port=8080)

    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    print(f"\n✅ Authorization successful! Token saved to: {TOKEN_FILE}")


if __name__ == "__main__":
    authenticate()
