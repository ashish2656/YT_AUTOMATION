#!/usr/bin/env python3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/youtube.upload'
]

# Channel folder mappings from config
folders = {
    3: ('1jzhyjsiKPRWJSZZSsasz4qq8Kq9qapV5', 'ashish2656 -> Satisfying'),
    4: ('1z57u3QvY5BE5uZWQ4UA5x5HPXX0vQ4TE', 'ajay5151 -> 4k reels'),
    5: ('1zjcqYUmE0Dzp6Jtuv-jy7fl4_D5WZFEg', 'ashish269697 -> Mixed Content')
}

for account_num, (folder_id, channel_name) in folders.items():
    print(f"\n{'='*60}")
    print(f"Account {account_num}: {channel_name}")
    print(f"Folder ID: {folder_id}")
    
    try:
        # Try to load token
        with open(f'token_account{account_num}.json', 'r') as f:
            token_data = json.load(f)
        
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        drive = build('drive', 'v3', credentials=creds)
        
        # Try to access folder
        folder = drive.files().get(fileId=folder_id, fields='id, name').execute()
        print(f"  ✅ Token valid - Folder: {folder.get('name')}")
        
        # Count videos
        results = drive.files().list(
            q=f"'{folder_id}' in parents and mimeType contains 'video/' and trashed = false",
            pageSize=1000,
            fields='files(id)'
        ).execute()
        
        video_count = len(results.get('files', []))
        print(f"  📹 Videos in folder: {video_count}")
        
        if video_count == 0:
            print(f"  ⚠️  FOLDER IS EMPTY - Need to add videos!")
        
    except Exception as e:
        error_msg = str(e)
        if 'invalid_grant' in error_msg or 'expired' in error_msg:
            print(f"  ❌ Token expired/invalid - NEEDS REGENERATION")
        elif '404' in error_msg or 'not found' in error_msg.lower():
            print(f"  ❌ Folder not accessible - Check sharing/permissions")
        else:
            print(f"  ❌ Error: {e}")

print(f"\n{'='*60}")
