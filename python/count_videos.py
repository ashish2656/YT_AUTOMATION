from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json

with open('token_account2.json') as f:
    token = json.load(f)
    
creds = Credentials.from_authorized_user_info(token, [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/youtube.upload'
])

drive = build('drive', 'v3', credentials=creds)

folder_id = '1oRMIuzjT3lRA5xTN5SB-TTlqqX-srWBp'

print('Counting all videos in folder...')

all_videos = []
page_token = None

while True:
    results = drive.files().list(
        q=f"'{folder_id}' in parents and mimeType contains 'video/' and trashed = false",
        pageSize=1000,
        pageToken=page_token,
        fields='nextPageToken, files(id, name)'
    ).execute()
    
    files = results.get('files', [])
    all_videos.extend(files)
    
    page_token = results.get('nextPageToken')
    if not page_token:
        break
    
    print(f'Fetched {len(all_videos)} videos so far...')

print(f'\n✅ Total videos in folder: {len(all_videos)}')
