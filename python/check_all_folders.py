from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json

# Use account1 or account2 token to check all folders
with open('token_account2.json') as f:
    token = json.load(f)
    
creds = Credentials.from_authorized_user_info(token, [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/youtube.upload'
])

drive = build('drive', 'v3', credentials=creds)

# All folder IDs from config
folders = {
    'channel_1 (Baddie)': '1oRMIuzjT3lRA5xTN5SB-TTlqqX-srWBp',
    'channel_3 (Satisfying)': '1jzhyjsiKPRWJSZZSsasz4qq8Kq9qapV5',
    'channel_4 (4k reels)': '1z57u3QvY5BE5uZWQ4UA5x5HPXX0vQ4TE',
    'channel_5 (Mixed Content)': '1zjcqYUmE0Dzp6Jtuv-jy7fl4_D5WZFEg'
}

print("Checking all Drive folders...\n")

for channel, folder_id in folders.items():
    try:
        folder = drive.files().get(fileId=folder_id, fields='id, name').execute()
        
        # Count videos
        all_videos = []
        page_token = None
        
        while True:
            results = drive.files().list(
                q=f"'{folder_id}' in parents and mimeType contains 'video/' and trashed = false",
                pageSize=1000,
                pageToken=page_token,
                fields='nextPageToken, files(id)'
            ).execute()
            
            files = results.get('files', [])
            all_videos.extend(files)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        
        print(f"✅ {channel}")
        print(f"   Folder: {folder['name']}")
        print(f"   Videos: {len(all_videos)}")
        print()
        
    except Exception as e:
        print(f"❌ {channel}")
        print(f"   Error: {str(e)[:100]}")
        print()
