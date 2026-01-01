import os
import io
import json
import sys
import tempfile
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from pymongo import MongoClient
from datetime import datetime
from metadata_manager import MetadataGenerator
import google.generativeai as genai

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

# Gemini AI Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip("'\"")

# OpenAI Configuration (fallback when Gemini quota exhausted)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip("'\"")

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
# Helper Functions
# ------------------------------
def extract_folder_id(folder_input):
    """
    Extract folder ID from Google Drive URL or return as-is if already an ID
    
    Args:
        folder_input (str): Either a folder ID or a full Google Drive URL
        
    Returns:
        str: The extracted folder ID or None if invalid
    """
    if not folder_input:
        return None
    
    folder_input = folder_input.strip()
    
    # If it's already a folder ID (no slashes), return it
    if "/" not in folder_input:
        return folder_input
    
    # Try to extract from URL patterns:
    # https://drive.google.com/drive/folders/FOLDER_ID
    # https://drive.google.com/drive/u/0/folders/FOLDER_ID
    if "drive.google.com" in folder_input:
        parts = folder_input.split("/folders/")
        if len(parts) > 1:
            # Get everything after /folders/ and before any query params
            folder_id = parts[1].split("?")[0].split("#")[0]
            return folder_id.strip()
    
    # If we can't parse it, return None
    return None

def analyze_video_with_gemini(video_buffer, filename, channel_name=""):
    """
    Analyze video with Google Gemini AI to generate title and description
    
    Args:
        video_buffer: BytesIO buffer containing video data
        filename: Original filename
        channel_name: Name of the channel for context
        
    Returns:
        dict: {"title": str, "description": str, "tags": list} or None if failed
    """
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY not set, skipping AI analysis", file=sys.stderr)
        print(f"DEBUG: GEMINI_API_KEY value: '{GEMINI_API_KEY[:10]}...' (length: {len(GEMINI_API_KEY) if GEMINI_API_KEY else 0})", file=sys.stderr)
        return None
    
    print(f"DEBUG: Using GEMINI_API_KEY (length: {len(GEMINI_API_KEY)})", file=sys.stderr)
    
    try:
        # Configure Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Save video to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            video_buffer.seek(0)
            tmp_file.write(video_buffer.read())
            tmp_path = tmp_file.name
        
        try:
            # Upload video to Gemini
            print(f"🤖 Uploading video to Gemini AI for analysis...", file=sys.stderr)
            video_file = genai.upload_file(tmp_path, mime_type="video/mp4")
            
            # Wait for processing (max 60 seconds)
            wait_time = 0
            while video_file.state.name == "PROCESSING" and wait_time < 60:
                time.sleep(2)
                wait_time += 2
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name != "ACTIVE":
                print(f"Warning: Video processing timed out or failed", file=sys.stderr)
                return None
            
            # Create prompt for Gemini
            prompt = f"""
You are a YouTube Shorts growth expert.

Analyze the provided short-form video and generate high-performing,
viral-ready metadata optimized for YouTube Shorts discovery.

Channel Name:
{channel_name}

CONTENT GUIDELINES:

1. TITLE
- Maximum 60 characters
- Curiosity-driven and emotionally engaging
- Designed to stop scrolling
- No emojis
- No misleading clickbait

2. DESCRIPTION
- Maximum 200 characters
- First line must hook the viewer
- Clearly describe what happens in the video
- Use SEO-friendly keywords naturally
- Encourage likes, comments, or shares

3. TAGS
- Exactly 5 trending hashtags
- Highly relevant to the video content
- Suitable for YouTube Shorts
- Lowercase only

STRICT OUTPUT FORMAT (JSON ONLY):
{
  "title": "string",
  "description": "string",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}

Focus on virality, retention, and click-through rate.
"""
            
            # Generate response using gemini-2.5-flash
            print(f"🧠 Analyzing video content...", file=sys.stderr)
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content([prompt, video_file])
            
            # Parse JSON response
            response_text = response.text.strip()
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
            
            metadata = json.loads(response_text)
            
            # Validate and clean metadata
            title = metadata.get("title", "")[:100]  # YouTube max title
            description = metadata.get("description", "")[:5000]  # YouTube max description
            tags = metadata.get("tags", [])[:15]  # Limit tags
            
            print(f"✅ AI Generated: {title}", file=sys.stderr)
            
            return {
                "title": title,
                "description": description,
                "tags": tags,
                "category_id": "24"  # Entertainment
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            # Delete uploaded file from Gemini
            try:
                genai.delete_file(video_file.name)
            except:
                pass
                
    except Exception as e:
        error_msg = str(e).lower()
        if "quota" in error_msg or "rate" in error_msg or "limit" in error_msg or "429" in error_msg:
            print(f"⚠️ Gemini quota exceeded: {e}", file=sys.stderr)
            return "QUOTA_EXCEEDED"  # Signal to try fallback
        print(f"Error in Gemini analysis: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


def analyze_video_with_openai(video_buffer, filename, channel_name=""):
    """
    Analyze video with OpenAI Vision API (extracts frames for analysis)
    Used as fallback when Gemini quota is exhausted
    
    Args:
        video_buffer: BytesIO buffer containing video data
        filename: Original filename
        channel_name: Name of the channel for context
        
    Returns:
        dict: {"title": str, "description": str, "tags": list} or None if failed
    """
    if not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY not set, cannot use OpenAI fallback", file=sys.stderr)
        return None
    
    try:
        import cv2
        import base64
        import numpy as np
        from openai import OpenAI
        
        # Initialize OpenAI client
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Save video to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            video_buffer.seek(0)
            tmp_file.write(video_buffer.read())
            tmp_path = tmp_file.name
        
        try:
            # Extract frames from video
            print(f"🎬 Extracting frames for OpenAI analysis...", file=sys.stderr)
            cap = cv2.VideoCapture(tmp_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Get 3 frames: beginning, middle, end
            frame_positions = [0, total_frames // 2, max(0, total_frames - 10)]
            encoded_frames = []
            
            for pos in frame_positions:
                cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
                ret, frame = cap.read()
                if ret:
                    # Resize frame to reduce token usage
                    frame = cv2.resize(frame, (512, 512))
                    # Encode to base64
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    encoded_frames.append(base64.b64encode(buffer).decode('utf-8'))
            
            cap.release()
            
            if not encoded_frames:
                print("Warning: Could not extract frames from video", file=sys.stderr)
                return None
            
            # Build messages with images
            print(f"🤖 Analyzing with OpenAI Vision...", file=sys.stderr)
            
            content = [
                {
                    "type": "text",
                    "text": f"""Analyze these frames from a YouTube Short video and generate engaging metadata.

Channel: {channel_name}
Filename: {filename}

Generate:
1. A catchy, viral-worthy title (max 60 characters) that will make people click
2. An SEO-optimized description (max 200 characters) with relevant keywords
3. 5 trending hashtags that match the video content

Respond ONLY with valid JSON:
{{
  "title": "your catchy title here",
  "description": "your SEO description here",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}"""
                }
            ]
            
            # Add frames to content
            for i, frame_data in enumerate(encoded_frames):
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{frame_data}",
                        "detail": "low"  # Use low detail to save tokens
                    }
                })
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective vision model
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=300
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
            
            metadata = json.loads(response_text)
            
            # Validate and clean metadata
            title = metadata.get("title", "")[:100]
            description = metadata.get("description", "")[:5000]
            tags = metadata.get("tags", [])[:15]
            
            print(f"✅ OpenAI Generated: {title}", file=sys.stderr)
            
            return {
                "title": title,
                "description": description,
                "tags": tags,
                "category_id": "24"  # Entertainment
            }
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        print(f"Error in OpenAI analysis: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


def analyze_video_with_ai(video_buffer, filename, channel_name=""):
    """
    Analyze video with AI - tries Gemini first, falls back to OpenAI if quota exceeded
    
    Args:
        video_buffer: BytesIO buffer containing video data
        filename: Original filename
        channel_name: Name of the channel for context
        
    Returns:
        dict: {"title": str, "description": str, "tags": list} or None if all failed
    """
    # Try Gemini first
    if GEMINI_API_KEY:
        result = analyze_video_with_gemini(video_buffer, filename, channel_name)
        if result == "QUOTA_EXCEEDED":
            print("🔄 Switching to OpenAI fallback...", file=sys.stderr)
        elif result is not None:
            return result
    
    # Fallback to OpenAI
    if OPENAI_API_KEY:
        video_buffer.seek(0)  # Reset buffer position
        result = analyze_video_with_openai(video_buffer, filename, channel_name)
        if result is not None:
            return result
    
    # Both failed
    print("⚠️ All AI analysis failed, will use templates", file=sys.stderr)
    return None

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

def save_uploaded_video(drive_file_id, file_name, youtube_video_id, youtube_url, channel_id=None):
    """Save uploaded video to MongoDB with channel tracking"""
    db = get_mongo_db()
    if db is None:
        return False
    
    try:
        db.uploaded_videos.insert_one({
            "drive_file_id": drive_file_id,
            "file_name": file_name,
            "youtube_video_id": youtube_video_id,
            "youtube_url": youtube_url,
            "channel_id": channel_id,
            "uploaded_at": datetime.utcnow()
        })
        return True
    except Exception as e:
        print(f"Error saving uploaded video: {e}", file=sys.stderr)
        return False

def get_channel_upload_count(channel_id):
    """Get count of uploaded videos for a specific channel"""
    db = get_mongo_db()
    if db is None:
        return 0
    
    try:
        count = db.uploaded_videos.count_documents({"channel_id": channel_id})
        return count
    except Exception as e:
        print(f"Error getting upload count for channel {channel_id}: {e}", file=sys.stderr)
        return 0

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
def get_credentials_for_account(account_id="account1"):
    """Get credentials for a specific account"""
    # Try to load from token file first
    token_file = os.path.join(SCRIPT_DIR, f"token_{account_id}.json")
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as f:
                token_data = json.load(f)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            return creds
        except Exception as e:
            print(f"Failed to load token from {token_file}: {e}", file=sys.stderr)
    
    # Fallback: Load environment variable for the specific account
    token_env_var = f"GOOGLE_TOKEN_ACCOUNT{account_id[-1]}_JSON"
    token_json = os.environ.get(token_env_var)
    
    if token_json:
        try:
            # Remove surrounding quotes if present
            token_json = token_json.strip("'\"")
            token_data = json.loads(token_json)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            return creds
        except Exception as e:
            print(f"Failed to load token for {account_id}: {e}", file=sys.stderr)
    
    # Last fallback to default credentials (will trigger OAuth if needed)
    print(f"Warning: No token found for {account_id}, using default auth", file=sys.stderr)
    return get_credentials(load_config())

def get_credentials(config):
    # Load from environment variable or config
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
    """Get upload statistics from Google Drive across all channels"""
    config = load_config()
    metadata_gen = MetadataGenerator()
    channels = metadata_gen.get_enabled_channels()
    
    total = 0
    
    # Aggregate stats across all enabled channels with drive_folder_id set
    for channel in channels:
        if not channel.get("enabled", True):
            continue
        
        folder_id = channel.get("drive_folder_id", "").strip()
        if not folder_id:
            continue
        
        # Extract folder ID from URL if needed
        folder_id = extract_folder_id(folder_id)
        if not folder_id:
            print(f"Warning: Invalid folder_id for channel {channel['name']}", file=sys.stderr)
            continue
        
        try:
            account_id = channel.get("youtube_account", "account1")
            creds = get_credentials_for_account(account_id)
            drive_service = build("drive", "v3", credentials=creds)
            
            page_token = None
            while True:
                results = drive_service.files().list(
                    q=f"'{folder_id}' in parents and mimeType contains 'video/' and trashed = false",
                    pageSize=100,
                    pageToken=page_token,
                    fields="nextPageToken, files(id)"
                ).execute()
                
                total += len(results.get("files", []))
                page_token = results.get("nextPageToken")
                
                if not page_token:
                    break
        except Exception as e:
            print(f"Warning: Failed to get stats for channel {channel['name']}: {e}", file=sys.stderr)
            continue
    
    uploaded_ids, _ = load_uploaded_videos()
    uploaded = len(uploaded_ids)
    
    return {"total": total, "uploaded": uploaded, "pending": total - uploaded}

def get_videos(limit=20, channel_id=None):
    """Get list of videos from Google Drive for specific channel or all channels"""
    config = load_config()
    metadata_gen = MetadataGenerator()
    channels = metadata_gen.get_enabled_channels()
    
    # Filter to specific channel if provided
    if channel_id:
        channels = [ch for ch in channels if ch["id"] == channel_id]
        if not channels:
            return []
    
    uploaded_ids, _ = load_uploaded_videos()
    videos = []
    
    # Aggregate videos across selected channels with drive_folder_id set
    for channel in channels:
        if not channel.get("enabled", True):
            continue
        
        folder_id = channel.get("drive_folder_id", "").strip()
        if not folder_id:
            continue
        
        # Extract folder ID from URL if needed
        folder_id = extract_folder_id(folder_id)
        if not folder_id:
            print(f"Warning: Invalid folder_id for channel {channel['name']}", file=sys.stderr)
            continue
        
        try:
            account_id = channel.get("youtube_account", "account1")
            creds = get_credentials_for_account(account_id)
            drive_service = build("drive", "v3", credentials=creds)
            
            results = drive_service.files().list(
                q=f"'{folder_id}' in parents and mimeType contains 'video/' and trashed = false",
                orderBy="createdTime asc",
                pageSize=limit,
                fields="files(id, name, size)"
            ).execute()
            
            for f in results.get("files", []):
                size_bytes = int(f.get("size", 0))
                size_mb = f"{size_bytes / (1024*1024):.1f} MB" if size_bytes > 0 else "Unknown"
                videos.append({
                    "id": f["id"],
                    "name": f["name"],
                    "size": size_mb,
                    "channel": channel["name"],
                    "status": "uploaded" if f["id"] in uploaded_ids else "pending"
                })
        except Exception as e:
            print(f"Warning: Failed to get videos for channel {channel['name']}: {e}", file=sys.stderr)
            continue
    
    # Sort by name and limit
    videos.sort(key=lambda x: x["name"])
    return videos[:limit]

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

def upload_next(channel_id=None):
    """Upload the next pending video to YouTube using specified channel"""
    config = load_config()
    
    # Get channel info
    metadata_gen = MetadataGenerator()
    channels = metadata_gen.get_enabled_channels()
    
    # Find the specified channel or use first available
    target_channel = None
    if channel_id:
        for ch in channels:
            if ch["id"] == channel_id:
                target_channel = ch
                break
    
    if not target_channel:
        # Try to find any channel with drive_folder_id
        for ch in channels:
            if ch.get("drive_folder_id"):
                target_channel = ch
                break
    
    if not target_channel:
        return {
            "success": False, 
            "error": "No channel found with drive_folder_id configured"
        }
    
    if not target_channel.get("drive_folder_id"):
        return {
            "success": False,
            "error": f"Channel '{target_channel['name']}' has no drive_folder_id configured"
        }
    
    account_id = target_channel.get("youtube_account", "account1")
    folder_id = target_channel["drive_folder_id"]
    
    # Extract folder ID from URL if needed
    folder_id = extract_folder_id(folder_id)
    if not folder_id:
        return {
            "success": False,
            "error": f"Invalid drive_folder_id for channel '{target_channel['name']}'"
        }
    
    # Get credentials for the channel's account
    creds = get_credentials_for_account(account_id)
    
    drive_service = build("drive", "v3", credentials=creds)
    youtube_service = build("youtube", "v3", credentials=creds)
    
    uploaded_ids, uploaded_titles = load_uploaded_videos()
    
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and mimeType contains 'video/' and trashed = false",
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
    
    # Check if channel uses AI metadata generation
    use_ai = target_channel.get("use_ai_metadata", True)  # Default to True
    
    video_title = None
    video_description = None
    video_tags = None
    category_id = "24"
    
    # Try AI analysis first if enabled
    if use_ai:
        print(f"🎬 Using AI to analyze video...", file=sys.stderr)
        ai_metadata = analyze_video_with_ai(
            video_buffer, 
            file_name, 
            target_channel.get("name", "")
        )
        
        if ai_metadata:
            video_title = ai_metadata["title"]
            video_description = ai_metadata["description"]
            video_tags = ai_metadata["tags"]
            category_id = ai_metadata.get("category_id", "24")
            print(f"✅ Using AI-generated metadata", file=sys.stderr)
        else:
            print(f"⚠️ AI analysis failed, falling back to templates", file=sys.stderr)
    
    # Fallback to templates if AI disabled or failed
    if not video_title:
        try:
            print(f"📝 Using channel templates", file=sys.stderr)
            metadata = metadata_gen.generate_metadata(target_channel["id"], file_name)
            video_title = metadata["title"]
            video_description = metadata["description"]
            video_tags = metadata["tags"]
            category_id = metadata.get("category_id", "24")
        except Exception as e:
            print(f"Warning: Failed to generate metadata, using defaults: {e}", file=sys.stderr)
            video_title = file_name
            video_description = target_channel.get("name", "") + " #Shorts"
            video_tags = ["Shorts"]
            category_id = "24"
    
    # Upload directly from memory to YouTube
    media = MediaIoBaseUpload(video_buffer, mimetype=mime_type, chunksize=-1, resumable=True)
    
    request = youtube_service.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": video_title,
                "description": video_description,
                "tags": video_tags,
                "categoryId": category_id
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=media
    )
    
    response = request.execute()
    video_id = response['id']
    youtube_url = f"https://www.youtube.com/shorts/{video_id}"
    
    # Save to MongoDB with channel info
    video_doc = {
        "drive_file_id": file_id,
        "file_name": file_name,
        "youtube_video_id": video_id,
        "youtube_url": youtube_url,
        "uploaded_at": datetime.now().isoformat(),
        "channel_id": target_channel["id"],
        "youtube_account": account_id,
        "title": video_title,
        "description": video_description,
        "tags": video_tags
    }
    save_uploaded_video(file_id, file_name, video_id, youtube_url, target_channel["id"])
    
    return {
        "success": True,
        "videoId": video_id,
        "fileName": file_name,
        "youtubeUrl": youtube_url,
        "channel": target_channel["name"],
        "account": account_id,
        "metadata": {
            "title": video_title,
            "description": video_description[:100] + "...",
            "tags": video_tags[:5]
        }
    }

def upload_all_channels():
    """Upload one video from each enabled channel"""
    metadata_gen = MetadataGenerator()
    channels = metadata_gen.get_enabled_channels()
    
    # Filter channels with drive_folder_id configured
    valid_channels = [ch for ch in channels if ch.get("drive_folder_id")]
    
    if not valid_channels:
        return {
            "success": False,
            "error": "No channels with drive_folder_id configured"
        }
    
    results = []
    success_count = 0
    error_count = 0
    
    for channel in valid_channels:
        try:
            print(f"\n📤 Uploading from channel: {channel['name']}...", file=sys.stderr)
            result = upload_next(channel["id"])
            
            if result.get("success"):
                success_count += 1
                results.append({
                    "channel": channel["name"],
                    "channel_id": channel["id"],
                    "success": True,
                    "videoId": result.get("videoId"),
                    "title": result.get("metadata", {}).get("title", ""),
                    "youtubeUrl": result.get("youtubeUrl")
                })
                print(f"✅ {channel['name']}: Uploaded successfully", file=sys.stderr)
            else:
                error_count += 1
                results.append({
                    "channel": channel["name"],
                    "channel_id": channel["id"],
                    "success": False,
                    "error": result.get("error", "Unknown error")
                })
                print(f"❌ {channel['name']}: {result.get('error')}", file=sys.stderr)
                
        except Exception as e:
            error_count += 1
            results.append({
                "channel": channel["name"],
                "channel_id": channel["id"],
                "success": False,
                "error": str(e)
            })
            print(f"❌ {channel['name']}: {str(e)}", file=sys.stderr)
    
    return {
        "success": success_count > 0,
        "total_channels": len(valid_channels),
        "success_count": success_count,
        "error_count": error_count,
        "results": results
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
    save_uploaded_video(drive_file_id, file_name, video_id, youtube_url, None)
    
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
            channel_id = sys.argv[3] if len(sys.argv) > 3 else None
            print(json.dumps(get_videos(limit, channel_id)))
        
        elif cmd == "history":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            print(json.dumps(get_uploaded_history(limit)))
        
        elif cmd == "config":
            print(json.dumps(load_config()))
        
        elif cmd == "upload":
            channel_id = None
            video_id = None
            
            # Parse arguments: can be upload [video_id] [channel_id] or upload [channel_id]
            if len(sys.argv) > 2:
                first_arg = sys.argv[2]
                # Check if first arg looks like channel_id (starts with 'channel')
                if first_arg.startswith('channel'):
                    channel_id = first_arg
                else:
                    video_id = first_arg
                    # Check for channel_id as third arg
                    if len(sys.argv) > 3:
                        channel_id = sys.argv[3]
            
            if video_id:
                result = upload_specific(video_id)
            else:
                result = upload_next(channel_id)
            print(json.dumps(result))
        
        elif cmd == "upload-all":
            # Upload one video from each enabled channel
            result = upload_all_channels()
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
        
        elif cmd == "channels":
            # Multi-channel management commands
            metadata_gen = MetadataGenerator()
            
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Missing channels subcommand"}))
            else:
                sub_cmd = sys.argv[2]
                
                if sub_cmd == "list":
                    config = metadata_gen.load_channels_config()
                    channels = config.get("channels", [])
                    
                    # Add upload count to each channel
                    for channel in channels:
                        channel["uploaded_count"] = get_channel_upload_count(channel.get("id"))
                    
                    print(json.dumps({"success": True, "channels": channels}))
                
                elif sub_cmd == "create":
                    if len(sys.argv) < 4:
                        print(json.dumps({"error": "Missing channel configuration JSON"}))
                    else:
                        try:
                            channel_data = json.loads(sys.argv[3])
                            config = metadata_gen.load_channels_config()
                            channels = config.get("channels", [])
                            
                            # Generate new ID
                            new_id = f"channel_{len(channels) + 1}"
                            channel_data["id"] = new_id
                            channel_data["enabled"] = channel_data.get("enabled", True)
                            
                            channels.append(channel_data)
                            config["channels"] = channels
                            metadata_gen.save_channels_config(config)
                            print(json.dumps({"success": True, "channel": channel_data}))
                        except Exception as e:
                            print(json.dumps({"success": False, "error": str(e)}))
                
                elif sub_cmd == "update":
                    if len(sys.argv) < 5:
                        print(json.dumps({"error": "Missing channel ID or configuration JSON"}))
                    else:
                        try:
                            channel_id = sys.argv[3]
                            update_data = json.loads(sys.argv[4])
                            config = metadata_gen.load_channels_config()
                            channels = config.get("channels", [])
                            
                            updated = False
                            for i, ch in enumerate(channels):
                                if ch["id"] == channel_id:
                                    channels[i].update(update_data)
                                    updated = True
                                    break
                            
                            if updated:
                                config["channels"] = channels
                                metadata_gen.save_channels_config(config)
                                print(json.dumps({"success": True, "channel": channels[i]}))
                            else:
                                print(json.dumps({"success": False, "error": "Channel not found"}))
                        except Exception as e:
                            print(json.dumps({"success": False, "error": str(e)}))
                
                elif sub_cmd == "delete":
                    if len(sys.argv) < 4:
                        print(json.dumps({"error": "Missing channel ID"}))
                    else:
                        channel_id = sys.argv[3]
                        config = metadata_gen.load_channels_config()
                        channels = config.get("channels", [])
                        channels = [ch for ch in channels if ch["id"] != channel_id]
                        config["channels"] = channels
                        metadata_gen.save_channels_config(config)
                        print(json.dumps({"success": True}))
                
                elif sub_cmd == "toggle":
                    if len(sys.argv) < 4:
                        print(json.dumps({"error": "Missing channel ID"}))
                    else:
                        channel_id = sys.argv[3]
                        config = metadata_gen.load_channels_config()
                        channels = config.get("channels", [])
                        
                        for ch in channels:
                            if ch["id"] == channel_id:
                                ch["enabled"] = not ch.get("enabled", True)
                                break
                        
                        config["channels"] = channels
                        metadata_gen.save_channels_config(config)
                        print(json.dumps({"success": True}))
                
                else:
                    print(json.dumps({"error": f"Unknown channels subcommand: {sub_cmd}"}))
        
        elif cmd == "metadata":
            # Metadata generation commands
            metadata_gen = MetadataGenerator()
            
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Missing metadata subcommand"}))
            else:
                sub_cmd = sys.argv[2]
                
                if sub_cmd == "generate":
                    if len(sys.argv) < 5:
                        print(json.dumps({"error": "Missing channel_id or filename"}))
                    else:
                        try:
                            channel_id = sys.argv[3]
                            filename = sys.argv[4]
                            metadata = metadata_gen.generate_metadata(channel_id, filename)
                            print(json.dumps({"success": True, "metadata": metadata}))
                        except Exception as e:
                            print(json.dumps({"success": False, "error": str(e)}))
                
                elif sub_cmd == "trending":
                    try:
                        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
                        hashtags = metadata_gen.get_top_hashtags(limit)
                        categories = list(set([row.get("category", "General") for row in metadata_gen.load_csv_data("youtube_shorts_tiktok_trends_2025.csv")[:100]]))
                        print(json.dumps({
                            "success": True,
                            "hashtags": hashtags,
                            "categories": categories[:10]
                        }))
                    except Exception as e:
                        print(json.dumps({"success": False, "error": str(e)}))
                
                else:
                    print(json.dumps({"error": f"Unknown metadata subcommand: {sub_cmd}"}))
        
        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
    else:
        # Default: upload next video
        result = upload_next()
        print(json.dumps(result))
