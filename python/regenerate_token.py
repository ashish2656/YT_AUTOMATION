#!/usr/bin/env python3
"""
Regenerate tokens for accounts 3, 4, and 5
Run this for each account one at a time
"""

import os
import sys
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/drive.readonly"
]

# Account mapping
ACCOUNTS = {
    "3": "ashishdodiya2656@gmail.com",
    "4": "ajaydodiya5151@gmail.com", 
    "5": "ashishdodiya269697@gmail.com"
}

if len(sys.argv) < 2:
    print("Usage: python3 regenerate_token.py <account_number>")
    print("\nAvailable accounts:")
    for num, email in ACCOUNTS.items():
        print(f"  {num}: {email}")
    sys.exit(1)

account_num = sys.argv[1]

if account_num not in ACCOUNTS:
    print(f"❌ Invalid account number: {account_num}")
    print(f"Valid options: {', '.join(ACCOUNTS.keys())}")
    sys.exit(1)

email = ACCOUNTS[account_num]

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

print(f"🔑 Regenerating token for Account {account_num}")
print(f"📧 Email: {email}")
print("\nIMPORTANT:")
print(f"1. A browser window will open")
print(f"2. Sign in with: {email}")
print(f"3. Grant permissions")
print()

# Create flow
flow = InstalledAppFlow.from_client_config(credentials, SCOPES)
creds = flow.run_local_server(port=8080)

# Save token
token_data = json.loads(creds.to_json())
output_file = f'token_account{account_num}.json'

with open(output_file, 'w') as f:
    json.dump(token_data, f, indent=2)

print(f"\n✅ Token saved to {output_file}")
print("\nNext step:")
print(f"Update GitHub secret: GOOGLE_TOKEN_ACCOUNT{account_num}_JSON")
print(f"with the content of {output_file}")
