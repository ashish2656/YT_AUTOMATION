#!/usr/bin/env python3
"""
Regenerate token for account2 (ashishdodiya5151@gmail.com)
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/drive.readonly"
]

# Load credentials from config.json
with open('config.json', 'r') as f:
    config = json.load(f)

credentials = {
    "installed": {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "redirect_uris": ["http://localhost"]
    }
}

print("🔑 Regenerating token for Account 2 (ashishdodiya5151@gmail.com)")
print("\nIMPORTANT:")
print("1. A browser window will open")
print("2. Sign in with: ashishdodiya5151@gmail.com")
print("3. Grant permissions")
print()

# Create flow
flow = InstalledAppFlow.from_client_config(credentials, SCOPES)
creds = flow.run_local_server(port=8080)

# Save token
token_data = json.loads(creds.to_json())

with open('token_account2.json', 'w') as f:
    json.dump(token_data, f, indent=2)

print("\n✅ Token saved to token_account2.json")
print("\nNext steps:")
print("1. Test the token by running the workflow")
print("2. Update GitHub secret: GOOGLE_TOKEN_ACCOUNT2_JSON with the content of token_account2.json")
