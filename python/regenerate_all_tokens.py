#!/usr/bin/env python3
"""
Regenerate tokens for accounts 3, 4, 5
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

accounts = {
    3: "ashishdodiya2656@gmail.com",
    4: "ajaydodiya5151@gmail.com", 
    5: "ashishdodiya269697@gmail.com"
}

for account_num, email in accounts.items():
    print(f"\n{'='*60}")
    print(f"🔑 Regenerating token for Account {account_num}")
    print(f"   Email: {email}")
    print("\nIMPORTANT:")
    print(f"1. A browser window will open")
    print(f"2. Sign in with: {email}")
    print(f"3. Grant permissions")
    print()
    
    input("Press Enter when ready...")
    
    # Create flow
    flow = InstalledAppFlow.from_client_config(credentials, SCOPES)
    creds = flow.run_local_server(port=8080)  # Use same port 8080 for all
    
    # Save token
    token_data = json.loads(creds.to_json())
    
    filename = f'token_account{account_num}.json'
    with open(filename, 'w') as f:
        json.dump(token_data, f, indent=2)
    
    print(f"\n✅ Token saved to {filename}")

print("\n" + "="*60)
print("✅ All tokens regenerated!")
print("\nNext: Check drive folders and update GitHub secrets")
