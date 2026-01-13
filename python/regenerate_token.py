#!/usr/bin/env python3
"""
Regenerate OAuth tokens for YouTube automation accounts.
This ensures tokens have refresh_token field for long-term use.
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/drive.readonly"
]

# Get OAuth credentials from environment or config.json
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Fallback to config.json if env vars not set
if not CLIENT_ID or not CLIENT_SECRET:
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            CLIENT_ID = config.get("client_id")
            CLIENT_SECRET = config.get("client_secret")
    except:
        pass

if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: OAuth credentials not found!")
    print("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables")
    print("Or ensure config.json contains client_id and client_secret")
    exit(1)

CLIENT_CONFIG = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }
}

def regenerate_token(email):
    """Generate fresh OAuth token with refresh_token"""
    print(f"\n🔑 Generating token for {email}...")
    print("=" * 60)
    
    # Create OAuth flow with offline access to get refresh_token
    flow = InstalledAppFlow.from_client_config(
        CLIENT_CONFIG, 
        SCOPES,
        redirect_uri='http://localhost:8080/'
    )
    
    # Force consent screen to get refresh_token every time
    flow.oauth2session.scope = SCOPES
    
    # Run OAuth flow (will open browser) - use port 8080 that's already configured
    creds = flow.run_local_server(
        port=8080,
        prompt='consent',  # Force consent to get refresh_token
        access_type='offline'  # Request offline access
    )
    
    # Save token with email as filename
    token_file = f"token_{email}.json"
    with open(token_file, "w") as f:
        f.write(creds.to_json())
    
    # Verify refresh_token is present
    with open(token_file, "r") as f:
        token_data = json.load(f)
    
    if "refresh_token" in token_data:
        print(f"✅ Token generated successfully: {token_file}")
        print(f"   Refresh token: {'*' * 20}{token_data['refresh_token'][-10:]}")
        return True
    else:
        print(f"⚠️  Warning: refresh_token not found in {token_file}")
        print("   Token may expire after 1 hour")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 regenerate_token.py <email>")
        print("Example: python3 regenerate_token.py ashishdodiya5151@gmail.com")
        print("\nAvailable accounts:")
        print("  ashishdodiya5151@gmail.com")
        print("  ashishdodiya2656@gmail.com")
        print("  ajaydodiya5151@gmail.com")
        print("  ashishdodiya269697@gmail.com")
        sys.exit(1)
    
    email = sys.argv[1]
    regenerate_token(email)
