import os
import io
import json
import sys
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# ------------------------------
# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# CONFIG FILES (relative to script directory)
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
UPLOADED_TRACKER = os.path.join(SCRIPT_DIR, "uploaded_videos.json")
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.json")

# Default config - credentials loaded from environment or .env file
ENV_FILE = os.path.join(SCRIPT_DIR, ".env")

def load_env():
    """Load environment variables from .env file"""
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

DEFAULT_CONFIG = {
    "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
    "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    "drive_folder_id": os.environ.get("DRIVE_FOLDER_ID", ""),
    "video_title": "Anime Edits #Shorts",
    "video_description": "🔥 Anime Edit Madness! 🔥\nGet ready to dive into a world of epic anime moments, insane fights, and unforgettable emotions.\n\n#AnimeEdits #AnimeEdit #OtakuVibes #AnimeLovers #EpicAnime #Shorts",
    "video_tags": ["AnimeEdits", "AnimeEdit", "OtakuVibes", "AnimeLovers", "EpicAnime", "Anime", "Shorts"]
}

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/youtube.upload"
]

# ------------------------------
# Config Management
# ------------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def load_uploaded_ids():
    if os.path.exists(UPLOADED_TRACKER):
        with open(UPLOADED_TRACKER, "r") as f:
            return set(json.load(f))
    return set()

def save_uploaded_id(video_id):
    uploaded_ids = load_uploaded_ids()
    uploaded_ids.add(video_id)
    with open(UPLOADED_TRACKER, "w") as f:
        json.dump(list(uploaded_ids), f)

# ------------------------------
# Authentication
# ------------------------------
def get_credentials(config):
    # First try to load from environment variable (for cloud deployment)
    token_json = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json:
        try:
            token_data = json.loads(token_json)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            return creds
        except Exception as e:
            print(f"Failed to load token from env: {e}", file=sys.stderr)
    
    # Then try to load from file
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        return creds
    
    # If no token exists, try to authenticate (only works locally)
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        SCOPES
    )
    creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    print("Authentication complete!")
    return creds

# ------------------------------
# API Functions
# ------------------------------
def get_stats():
    """Get upload statistics from Google Drive"""
    config = load_config()
    creds = get_credentials(config)
    drive_service = build("drive", "v3", credentials=creds)
    
    results = drive_service.files().list(
        q=f"'{config['drive_folder_id']}' in parents and mimeType contains 'video/' and trashed = false",
        pageSize=1000,
        fields="files(id)"
    ).execute()
    
    total = len(results.get("files", []))
    uploaded_ids = load_uploaded_ids()
    uploaded = len(uploaded_ids)
    
    return {"total": total, "uploaded": uploaded, "pending": total - uploaded}

def get_videos(limit=20):
    """Get list of videos from Google Drive"""
    config = load_config()
    creds = get_credentials(config)
    drive_service = build("drive", "v3", credentials=creds)
    
    results = drive_service.files().list(
        q=f"'{config['drive_folder_id']}' in parents and mimeType contains 'video/' and trashed = false",
        orderBy="createdTime asc",
        pageSize=limit,
        fields="files(id, name, size)"
    ).execute()
    
    uploaded_ids = load_uploaded_ids()
    videos = []
    
    for f in results.get("files", []):
        size_bytes = int(f.get("size", 0))
        size_mb = f"{size_bytes / (1024*1024):.1f} MB" if size_bytes > 0 else "Unknown"
        videos.append({
            "id": f["id"],
            "name": f["name"],
            "size": size_mb,
            "status": "uploaded" if f["id"] in uploaded_ids else "pending"
        })
    
    return videos

def upload_next():
    """Upload the next pending video to YouTube"""
    config = load_config()
    creds = get_credentials(config)
    
    drive_service = build("drive", "v3", credentials=creds)
    youtube = build("youtube", "v3", credentials=creds)
    
    uploaded_ids = load_uploaded_ids()
    
    results = drive_service.files().list(
        q=f"'{config['drive_folder_id']}' in parents and mimeType contains 'video/' and trashed = false",
        orderBy="createdTime asc",
        pageSize=100,
        fields="files(id, name, mimeType)"
    ).execute()
    
    available_videos = [f for f in results.get("files", []) if f["id"] not in uploaded_ids]
    
    if not available_videos:
        return {"success": False, "error": "No videos left to upload"}
    
    file = available_videos[0]
    file_id = file["id"]
    file_name = file["name"]
    mime_type = file.get("mimeType", "video/mp4")
    
    # Stream from Drive to memory
    request = drive_service.files().get_media(fileId=file_id)
    video_buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(video_buffer, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    
    video_buffer.seek(0)
    
    # Upload directly from memory to YouTube
    media = MediaIoBaseUpload(video_buffer, mimetype=mime_type, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": config["video_title"],
                "description": config["video_description"],
                "tags": config["video_tags"],
                "categoryId": "24"
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=media
    )
    
    response = request.execute()
    video_id = response['id']
    
    save_uploaded_id(file_id)
    
    return {
        "success": True,
        "videoId": video_id,
        "fileName": file_name,
        "youtubeUrl": f"https://www.youtube.com/shorts/{video_id}"
    }

def upload_specific(drive_file_id):
    """Upload a specific video by its Drive file ID"""
    config = load_config()
    creds = get_credentials(config)
    
    drive_service = build("drive", "v3", credentials=creds)
    youtube = build("youtube", "v3", credentials=creds)
    
    # Get file info
    file = drive_service.files().get(fileId=drive_file_id, fields="id, name, mimeType").execute()
    file_name = file["name"]
    mime_type = file.get("mimeType", "video/mp4")
    
    # Stream from Drive to memory
    request = drive_service.files().get_media(fileId=drive_file_id)
    video_buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(video_buffer, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    
    video_buffer.seek(0)
    
    # Upload directly from memory to YouTube
    media = MediaIoBaseUpload(video_buffer, mimetype=mime_type, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": config["video_title"],
                "description": config["video_description"],
                "tags": config["video_tags"],
                "categoryId": "24"
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=media
    )
    
    response = request.execute()
    video_id = response['id']
    
    save_uploaded_id(drive_file_id)
    
    return {
        "success": True,
        "videoId": video_id,
        "fileName": file_name,
        "youtubeUrl": f"https://www.youtube.com/shorts/{video_id}"
    }

# ------------------------------
# CLI Interface
# ------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "stats":
            print(json.dumps(get_stats()))
        
        elif cmd == "videos":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            print(json.dumps(get_videos(limit)))
        
        elif cmd == "config":
            print(json.dumps(load_config()))
        
        elif cmd == "upload":
            if len(sys.argv) > 2:
                # Upload specific video by ID
                result = upload_specific(sys.argv[2])
            else:
                # Upload next pending video
                result = upload_next()
            print(json.dumps(result))
        
        elif cmd == "set-folder" and len(sys.argv) > 2:
            config = load_config()
            config["drive_folder_id"] = sys.argv[2]
            save_config(config)
            print(json.dumps({"success": True, "folder_id": sys.argv[2]}))
        
        elif cmd == "set-title" and len(sys.argv) > 2:
            config = load_config()
            config["video_title"] = sys.argv[2]
            save_config(config)
            print(json.dumps({"success": True}))
        
        elif cmd == "set-description" and len(sys.argv) > 2:
            config = load_config()
            config["video_description"] = sys.argv[2]
            save_config(config)
            print(json.dumps({"success": True}))
        
        elif cmd == "set-tags" and len(sys.argv) > 2:
            config = load_config()
            config["video_tags"] = sys.argv[2].split(",")
            save_config(config)
            print(json.dumps({"success": True}))
        
        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
    else:
        # Default: upload next video
        result = upload_next()
        print(json.dumps(result))
