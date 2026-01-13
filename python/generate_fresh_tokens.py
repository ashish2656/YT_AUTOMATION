#!/usr/bin/env python3
"""
Generate fresh tokens for accounts 2, 3, 4, 5
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/drive.readonly"
]

# Load credentials
with open('config.json') as f:
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
    2: "ashishdodiya5151@gmail.com",
    3: "ashishdodiya2656@gmail.com",
    4: "ajaydodiya5151@gmail.com",
    5: "ashishdodiya269697@gmail.com"
}

print("🔑 Token Generation for YouTube Automation")
print("=" * 60)
print("\nIMPORTANT:")
print("- A browser will open for EACH account")
print("- Sign in with the CORRECT email for each")
print("- Grant all permissions")
print("=" * 60)

for account_num, email in accounts.items():
    print(f"\n\n{'='*60}")
    print(f"🔐 Account {account_num}: {email}")
    print('='*60)
    
    input(f"\nPress Enter to generate token for {email}...")
    
    try:
        flow = InstalledAppFlow.from_client_config(credentials, SCOPES)
        creds = flow.run_local_server(port=8080, open_browser=True)
        
        # Save token
        token_data = json.loads(creds.to_json())
        
        with open(f'token_account{account_num}.json', 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print(f"✅ Token saved: token_account{account_num}.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Skipping account {account_num}...")

print("\n\n" + "="*60)
print("✅ Token generation complete!")
print("="*60)
print("\nGenerated tokens:")
import os
for num in [2, 3, 4, 5]:
    if os.path.exists(f'token_account{num}.json'):
        print(f"  ✅ token_account{num}.json")
    else:
        print(f"  ❌ token_account{num}.json - MISSING")

print("\n📋 Next steps:")
print("1. Update GitHub secrets with new token files")
print("2. Test the workflow")
