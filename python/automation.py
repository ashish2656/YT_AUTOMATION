import os
import io
import json
import sys
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from pymongo import MongoClient
from datetime import datetime

# ------------------------------
# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# CONFIG FILES (relative to script directory)
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
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

# MongoDB Connection
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://ajyadodiya2003_db_user:AnPvBaCyJBI3XFp5@yt-automation.q12aqvq.mongodb.net/yt_automation?retryWrites=true&w=majority&appName=YT-Automation")

# Global MongoDB client (cached)
_mongo_client = None
_mongo_db = None

def get_mongo_db():
    """Get MongoDB database connection with caching"""
    global _mongo_client, _mongo_db
    
    if _mongo_db is not None:
        return _mongo_db
        
    if not MONGO_URI:
        print("Warning: MONGO_URI not set, using local file fallback", file=sys.stderr)
        return None
    try:
        # Add connection timeout to prevent hanging (reduced to 3 seconds)
        _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000, socketTimeoutMS=3000)
        _mongo_db = _mongo_client.yt_automation
        # Test connection with timeout
        _mongo_client.admin.command('ping')
        return _mongo_db
    except Exception as e:
        print(f"MongoDB connection error: {e}", file=sys.stderr)
        _mongo_client = None
        _mongo_db = None
        return None

# Fallback to local file tracking if MongoDB fails
UPLOADED_TRACKER = os.path.join(SCRIPT_DIR, "uploaded_videos.json")

def load_uploaded_ids_local():
    """Load uploaded IDs from local file (fallback)"""
    if os.path.exists(UPLOADED_TRACKER):
        with open(UPLOADED_TRACKER, "r") as f:
            return set(json.load(f))
    return set()

def save_uploaded_id_local(video_id):
    """Save uploaded ID to local file (fallback)"""
    uploaded_ids = load_uploaded_ids_local()
    uploaded_ids.add(video_id)
    with open(UPLOADED_TRACKER, "w") as f:
        json.dump(list(uploaded_ids), f)

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

# ------------------------------
# MongoDB - Uploaded Videos Tracking
# ------------------------------
def load_uploaded_videos():
    """Load uploaded videos from MongoDB with local fallback"""
    db = get_mongo_db()
    if db is None:
        # Fallback to local file
        local_ids = load_uploaded_ids_local()
        return local_ids, {}
    
    try:
        uploaded = db.uploaded_videos.find({})
        ids = set()
        titles = {}
        for doc in uploaded:
            ids.add(doc.get("drive_file_id", ""))
            title = doc.get("file_name", "")
            if title:
                titles[title.lower()] = doc.get("drive_file_id", "")
        return ids, titles
    except Exception as e:
        print(f"Error loading uploaded videos: {e}", file=sys.stderr)
        # Fallback to local file
        local_ids = load_uploaded_ids_local()
        return local_ids, {}

def save_uploaded_video(drive_file_id, file_name, youtube_video_id, youtube_url):
    """Save uploaded video to MongoDB"""
    db = get_mongo_db()
    if db is None:
        return False
    
    try:
        db.uploaded_videos.insert_one({
            "drive_file_id": drive_file_id,
            "file_name": file_name,
            "youtube_video_id": youtube_video_id,
            "youtube_url": youtube_url,
            "uploaded_at": datetime.utcnow()
        })
        return True
    except Exception as e:
        print(f"Error saving uploaded video: {e}", file=sys.stderr)
        return False

def is_video_uploaded(drive_file_id, file_name):
    """Check if video is already uploaded (by ID or title)"""
    uploaded_ids, uploaded_titles = load_uploaded_videos()
    
    # Check by Drive file ID
    if drive_file_id in uploaded_ids:
        return True
    
    # Check by file name (title match)
    if file_name.lower() in uploaded_titles:
        return True
    
    return False

# ------------------------------
# MongoDB - Token Management
# ------------------------------
def get_token_from_mongo():
    """Get YouTube token from MongoDB"""
    db = get_mongo_db()
    if db is None:
        return None
    
    try:
        token_doc = db.tokens.find_one({"type": "youtube"})
        if token_doc:
            return token_doc.get("token_data")
        return None
    except Exception as e:
        print(f"Error getting token from MongoDB: {e}", file=sys.stderr)
        return None

def save_token_to_mongo(token_data):
    """Save YouTube token to MongoDB"""
    db = get_mongo_db()
    if db is None:
        return False
    
    try:
        db.tokens.update_one(
            {"type": "youtube"},
            {"$set": {"token_data": token_data, "updated_at": datetime.utcnow()}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error saving token to MongoDB: {e}", file=sys.stderr)
        return False

def delete_token_from_mongo():
    """Delete YouTube token from MongoDB"""
    db = get_mongo_db()
    if db is None:
        return False
    
    try:
        db.tokens.delete_one({"type": "youtube"})
        return True
    except Exception as e:
        print(f"Error deleting token: {e}", file=sys.stderr)
        return False

# ------------------------------
# Authentication
# ------------------------------
def get_credentials(config):
    # Priority 1: MongoDB token
    mongo_token = get_token_from_mongo()
    if mongo_token:
        try:
            creds = Credentials.from_authorized_user_info(mongo_token, SCOPES)
            if creds and creds.valid:
                return creds
            # If expired but has refresh token, it will auto-refresh
            if creds and creds.expired and creds.refresh_token:
                return creds
        except Exception as e:
            print(f"Failed to load token from MongoDB: {e}", file=sys.stderr)
    
    # Priority 2: Environment variable (for backward compatibility)
    token_json = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json:
        try:
            token_data = json.loads(token_json)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            # Also save to MongoDB for future use
            save_token_to_mongo(token_data)
            return creds
        except Exception as e:
            print(f"Failed to load token from env: {e}", file=sys.stderr)
    
    # Priority 3: Local file
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        # Also save to MongoDB
        with open(TOKEN_FILE, "r") as f:
            save_token_to_mongo(json.load(f))
        return creds
    
    # Priority 4: OAuth flow (only works locally)
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
    
    # Save to file
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    
    # Save to MongoDB
    save_token_to_mongo(json.loads(creds.to_json()))
    
    print("Authentication complete!")
    return creds

# ------------------------------
# API Functions
# ------------------------------
def get_stats():
    """Get upload statistics from Google Drive (limited count for performance)"""
    config = load_config()
    creds = get_credentials(config)
    drive_service = build("drive", "v3", credentials=creds)
    
    # Only count up to 100 files for performance, use pageToken for actual count
    total = 0
    page_token = None
    
    while True:
        results = drive_service.files().list(
            q=f"'{config['drive_folder_id']}' in parents and mimeType contains 'video/' and trashed = false",
            pageSize=100,
            pageToken=page_token,
            fields="nextPageToken, files(id)"
        ).execute()
        
        total += len(results.get("files", []))
        page_token = results.get("nextPageToken")
        
        if not page_token:
            break
    
    uploaded_ids, _ = load_uploaded_videos()
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
    
    uploaded_ids, _ = load_uploaded_videos()
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

def get_uploaded_history(limit=50):
    """Get upload history from MongoDB"""
    db = get_mongo_db()
    if db is None:
        return []
    
    try:
        history = db.uploaded_videos.find({}).sort("uploaded_at", -1).limit(limit)
        result = []
        for doc in history:
            result.append({
                "file_name": doc.get("file_name", ""),
                "youtube_url": doc.get("youtube_url", ""),
                "uploaded_at": doc.get("uploaded_at", "").isoformat() if doc.get("uploaded_at") else ""
            })
        return result
    except Exception as e:
        print(f"Error getting upload history: {e}", file=sys.stderr)
        return []

def upload_next():
    """Upload the next pending video to YouTube"""
    config = load_config()
    creds = get_credentials(config)
    
    drive_service = build("drive", "v3", credentials=creds)
    youtube = build("youtube", "v3", credentials=creds)
    
    uploaded_ids, uploaded_titles = load_uploaded_videos()
    
    results = drive_service.files().list(
        q=f"'{config['drive_folder_id']}' in parents and mimeType contains 'video/' and trashed = false",
        orderBy="createdTime asc",
        pageSize=100,
        fields="files(id, name, mimeType)"
    ).execute()
    
    # Filter out already uploaded videos (by ID or title)
    available_videos = []
    for f in results.get("files", []):
        if f["id"] not in uploaded_ids and f["name"].lower() not in uploaded_titles:
            available_videos.append(f)
    
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
    youtube_url = f"https://www.youtube.com/shorts/{video_id}"
    
    # Save to MongoDB
    save_uploaded_video(file_id, file_name, video_id, youtube_url)
    
    return {
        "success": True,
        "videoId": video_id,
        "fileName": file_name,
        "youtubeUrl": youtube_url
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
    
    # Check if already uploaded
    if is_video_uploaded(drive_file_id, file_name):
        return {"success": False, "error": f"Video '{file_name}' has already been uploaded"}
    
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
    youtube_url = f"https://www.youtube.com/shorts/{video_id}"
    
    # Save to MongoDB
    save_uploaded_video(drive_file_id, file_name, video_id, youtube_url)
    
    return {
        "success": True,
        "videoId": video_id,
        "fileName": file_name,
        "youtubeUrl": youtube_url
    }

def switch_account():
    """Clear token to allow switching YouTube accounts"""
    # Delete from MongoDB (don't wait if it fails)
    try:
        delete_token_from_mongo()
    except:
        pass
    
    # Delete local token file
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
    
    return {"success": True, "message": "Token cleared. Re-authenticate to use a different account."}

def save_new_token(token_json_str):
    """Save a new token from JSON string"""
    try:
        token_data = json.loads(token_json_str)
        save_token_to_mongo(token_data)
        return {"success": True, "message": "Token saved to MongoDB"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_current_token():
    """Get current token info (without sensitive data)"""
    token = get_token_from_mongo()
    if token:
        return {
            "hasToken": True,
            "account": token.get("account", "Unknown"),
            "expiry": token.get("expiry", "Unknown")
        }
    return {"hasToken": False}

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
        
        elif cmd == "history":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            print(json.dumps(get_uploaded_history(limit)))
        
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
        
        elif cmd == "switch-account":
            result = switch_account()
            print(json.dumps(result))
        
        elif cmd == "save-token" and len(sys.argv) > 2:
            result = save_new_token(sys.argv[2])
            print(json.dumps(result))
        
        elif cmd == "token-info":
            print(json.dumps(get_current_token()))
        
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
