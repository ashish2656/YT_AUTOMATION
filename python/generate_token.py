#!/usr/bin/env python3
"""
Google OAuth Token Generator
Run this script to authenticate with Google and generate token.json
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from pymongo import MongoClient
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.json")

# Scopes for YouTube and Drive access
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/drive.readonly"
]

def load_env():
    """Load environment variables from .env file"""
    env_file = os.path.join(SCRIPT_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

def get_mongo_db():
    """Get MongoDB database connection"""
    load_env()
    mongo_uri = os.environ.get("MONGO_URI", "mongodb+srv://ajyadodiya2003_db_user:AnPvBaCyJBI3XFp5@yt-automation.q12aqvq.mongodb.net/yt_automation?retryWrites=true&w=majority&appName=YT-Automation")
    
    if not mongo_uri:
        print("⚠️  Warning: MONGO_URI not found in environment")
        return None
    
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client.yt_automation
        client.admin.command('ping')
        return db
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return None

def save_token_to_mongo(token_data):
    """Save token to MongoDB"""
    db = get_mongo_db()
    if db is None:
        return False
    
    try:
        db.tokens.update_one(
            {"type": "youtube"},
            {"$set": {"token_data": token_data, "updated_at": datetime.utcnow()}},
            upsert=True
        )
        print("✅ Token saved to MongoDB")
        return True
    except Exception as e:
        print(f"❌ Failed to save to MongoDB: {e}")
        return False

def get_credentials_json():
    """Get credentials from environment or create from Google Console"""
    load_env()
    
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("\n" + "=" * 60)
        print("⚠️  Google OAuth Credentials Not Found!")
        print("=" * 60)
        print("\nPlease provide your Google OAuth credentials.")
        print("\nOption 1: Add to .env file (recommended)")
        print("-" * 60)
        print("GOOGLE_CLIENT_ID=your_client_id_here")
        print("GOOGLE_CLIENT_SECRET=your_client_secret_here")
        print()
        print("Option 2: Enter them now")
        print("-" * 60)
        
        client_id = input("Enter Google Client ID: ").strip()
        client_secret = input("Enter Google Client Secret: ").strip()
        
        if not client_id or not client_secret:
            print("\n❌ Error: Both Client ID and Client Secret are required!")
            return None
    
    credentials = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost"]
        }
    }
    
    creds_file = os.path.join(SCRIPT_DIR, "credentials_temp.json")
    with open(creds_file, "w") as f:
        json.dump(credentials, f, indent=2)
    
    return creds_file

def main():
    print()
    print("=" * 60)
    print("🔐 Google OAuth Token Generator")
    print("=" * 60)
    print()
    
    # Get or create credentials
    creds_file = get_credentials_json()
    if not creds_file:
        return
    
    print("\n📝 Starting OAuth flow...")
    print("=" * 60)
    print("Your browser will open shortly. Please:")
    print("  1. Select your Google account")
    print("  2. Click 'Continue' even if you see 'App not verified'")
    print("  3. Grant permissions for YouTube and Drive")
    print("  4. Return here after authorization")
    print("=" * 60)
    print()
    input("Press ENTER to open browser and continue...")
    
    try:
        # Run OAuth flow with fixed port
        print("📌 Using redirect URI: http://localhost:8080/")
        print("   Make sure this EXACT URI is in your Google Cloud Console!\n")
        flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
        creds = flow.run_local_server(port=8080)
        
        # Convert credentials to dict
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
            "expiry": creds.expiry.isoformat() if creds.expiry else None
        }
        
        # Save to token.json
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f, indent=2)
        print(f"✅ Token saved to {TOKEN_FILE}")
        
        # Save to MongoDB
        save_token_to_mongo(token_data)
        
        # Clean up temp credentials file
        if os.path.exists(creds_file):
            os.remove(creds_file)
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Authentication Complete!")
        print("=" * 60)
        print(f"\n📄 Token file: {TOKEN_FILE}")
        print("💾 Token saved to MongoDB")
        print("\n🚀 You can now use the automation system!")
        print("=" * 60)
        print()
        
    except Exception as e:
        print(f"\n❌ Error during authentication: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your Google Client ID and Secret")
        print("  2. Ensure YouTube Data API v3 is enabled in Google Cloud")
        print("  3. Add http://localhost to OAuth redirect URIs")
        print("  4. Click 'Advanced' then 'Go to [app name]' if you see security warning")

if __name__ == "__main__":
    main()
