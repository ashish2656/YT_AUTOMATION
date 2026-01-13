#!/usr/bin/env python3
"""
Generate fresh tokens for all 5 accounts
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/drive.readonly"
]

# Load credentials
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
    1: "ajyadodiya2003@gmail.com",
    2: "ashishdodiya5151@gmail.com",
    3: "ashishdodiya2656@gmail.com",
    4: "ajaydodiya5151@gmail.com",
    5: "ashishdodiya269697@gmail.com"
}

print("🔑 Generating fresh tokens for all accounts\n")

for account_num, email in accounts.items():
    print(f"\n{'='*70}")
    print(f"Account {account_num}: {email}")
    print('='*70)
    print("A browser window will open. Sign in with this account and grant permissions.")
    input("\nPress Enter to continue...")
    
    try:
        flow = InstalledAppFlow.from_client_config(credentials, SCOPES)
        creds = flow.run_local_server(port=8080)
        
        token_data = json.loads(creds.to_json())
        
        with open(f'token_account{account_num}.json', 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print(f"✅ Token saved to token_account{account_num}.json")
        
    except Exception as e:
        print(f"❌ Error generating token for account {account_num}: {e}")

print("\n" + "="*70)
print("✅ Token generation complete!")
print("\nNext steps:")
print("1. Copy each token file content")
print("2. Update GitHub secrets:")
print("   - GOOGLE_TOKEN_ACCOUNT1_JSON")
print("   - GOOGLE_TOKEN_ACCOUNT2_JSON")
print("   - GOOGLE_TOKEN_ACCOUNT3_JSON")
print("   - GOOGLE_TOKEN_ACCOUNT4_JSON")
print("   - GOOGLE_TOKEN_ACCOUNT5_JSON")
