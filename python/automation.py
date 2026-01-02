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

# Together AI Configuration (LLaVA - LLaMA Vision, FREE $25 credits)
TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY", "").strip("'\"")

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
SUBFOLDER_TRACKER = os.path.join(SCRIPT_DIR, "subfolder_tracker.json")

def load_subfolder_tracker():
    """Load subfolder tracking data from MongoDB or local file"""
    db = get_mongo_db()
    if db is not None:
        try:
            tracker = db.subfolder_tracker.find_one({"_id": "tracker"})
            if tracker:
                return tracker.get("data", {})
        except Exception as e:
            print(f"Warning: Failed to load subfolder tracker from MongoDB: {e}", file=sys.stderr)
    
    # Fallback to local file
    if os.path.exists(SUBFOLDER_TRACKER):
        with open(SUBFOLDER_TRACKER, "r") as f:
            return json.load(f)
    return {}

def save_subfolder_tracker(data):
    """Save subfolder tracking data to MongoDB and local file"""
    # Save to local file first (backup)
    with open(SUBFOLDER_TRACKER, "w") as f:
        json.dump(data, f, indent=2)
    
    # Save to MongoDB
    db = get_mongo_db()
    if db is not None:
        try:
            db.subfolder_tracker.update_one(
                {"_id": "tracker"},
                {"$set": {"data": data, "updated_at": datetime.now()}},
                upsert=True
            )
        except Exception as e:
            print(f"Warning: Failed to save subfolder tracker to MongoDB: {e}", file=sys.stderr)

def get_subfolders_from_drive(drive_service, parent_folder_id):
    """
    Get all subfolders from a parent folder in Google Drive
    
    Args:
        drive_service: Google Drive API service
        parent_folder_id: ID of the parent folder
        
    Returns:
        list: List of subfolder dicts with id and name, sorted by name
    """
    try:
        subfolders = []
        page_token = None
        
        while True:
            results = drive_service.files().list(
                q=f"'{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                orderBy="name",
                pageSize=100,
                pageToken=page_token,
                fields="nextPageToken, files(id, name)"
            ).execute()
            
            subfolders.extend(results.get("files", []))
            page_token = results.get("nextPageToken")
            
            if not page_token:
                break
        
        return sorted(subfolders, key=lambda x: x["name"])
    except Exception as e:
        print(f"Error getting subfolders: {e}", file=sys.stderr)
        return []

def get_videos_from_folder(drive_service, folder_id, uploaded_ids, uploaded_titles):
    """
    Get available (not uploaded) videos from a specific folder
    
    Args:
        drive_service: Google Drive API service
        folder_id: ID of the folder to search
        uploaded_ids: Set of already uploaded video IDs
        uploaded_titles: Set of already uploaded video titles (lowercase)
        
    Returns:
        list: List of available video dicts
    """
    try:
        results = drive_service.files().list(
            q=f"'{folder_id}' in parents and mimeType contains 'video/' and trashed = false",
            orderBy="createdTime asc",
            pageSize=100,
            fields="files(id, name, mimeType)"
        ).execute()
        
        available_videos = []
        for f in results.get("files", []):
            if f["id"] not in uploaded_ids and f["name"].lower() not in uploaded_titles:
                available_videos.append(f)
        
        return available_videos
    except Exception as e:
        print(f"Error getting videos from folder: {e}", file=sys.stderr)
        return []

def get_next_video_with_subfolder_rotation(drive_service, main_folder_id, channel_id, uploaded_ids, uploaded_titles):
    """
    Get the next video to upload, automatically rotating through subfolders
    
    This function:
    1. Checks if main folder has subfolders
    2. If yes, tracks which subfolder is current and rotates when exhausted
    3. If no subfolders, treats main folder as video folder
    
    Args:
        drive_service: Google Drive API service
        main_folder_id: ID of the main/parent folder
        channel_id: Channel ID for tracking
        uploaded_ids: Set of already uploaded video IDs
        uploaded_titles: Set of already uploaded video titles
        
    Returns:
        tuple: (video_dict, current_subfolder_name) or (None, None) if no videos
    """
    # Get subfolders
    subfolders = get_subfolders_from_drive(drive_service, main_folder_id)
    
    # If no subfolders, treat main folder as video folder
    if not subfolders:
        print(f"📁 No subfolders found, using main folder directly", file=sys.stderr)
        videos = get_videos_from_folder(drive_service, main_folder_id, uploaded_ids, uploaded_titles)
        if videos:
            return videos[0], "main"
        return None, None
    
    print(f"📁 Found {len(subfolders)} subfolders: {[sf['name'] for sf in subfolders]}", file=sys.stderr)
    
    # Load tracker to find current subfolder
    tracker = load_subfolder_tracker()
    channel_tracker = tracker.get(channel_id, {})
    current_subfolder_index = channel_tracker.get("current_index", 0)
    
    # Try each subfolder starting from current
    for attempt in range(len(subfolders)):
        subfolder_index = (current_subfolder_index + attempt) % len(subfolders)
        subfolder = subfolders[subfolder_index]
        
        print(f"🔍 Checking subfolder: {subfolder['name']} (index {subfolder_index})", file=sys.stderr)
        
        videos = get_videos_from_folder(drive_service, subfolder["id"], uploaded_ids, uploaded_titles)
        
        if videos:
            # Update tracker if we moved to a different subfolder
            if subfolder_index != current_subfolder_index:
                print(f"📂 Switched to subfolder: {subfolder['name']}", file=sys.stderr)
                tracker[channel_id] = {
                    "current_index": subfolder_index,
                    "current_folder_id": subfolder["id"],
                    "current_folder_name": subfolder["name"],
                    "updated_at": datetime.now().isoformat()
                }
                save_subfolder_tracker(tracker)
            
            print(f"✅ Found {len(videos)} videos in: {subfolder['name']}", file=sys.stderr)
            return videos[0], subfolder["name"]
        else:
            print(f"⚠️ No videos left in: {subfolder['name']}", file=sys.stderr)
    
    # All subfolders exhausted
    print(f"❌ All subfolders exhausted for channel {channel_id}", file=sys.stderr)
    return None, None

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
            
            # Create prompt for Gemini - VIRAL optimized
            prompt = f"""You are an expert YouTube Shorts viral content strategist with 10+ years of experience.

Analyze this video and create VIRAL metadata that will EXPLODE on YouTube Shorts.

Channel: {channel_name}

🔥 VIRAL TITLE RULES:
- MAXIMUM 50 characters (YouTube cuts off longer titles)
- Use power words: "Insane", "Mind-Blowing", "You Won't Believe", "Secret", "Shocking", "Wait for it"
- Create curiosity gap - make them NEED to watch
- NO emojis, NO clickbait lies
- Pattern interrupt - something unexpected

💥 VIRAL DESCRIPTION RULES:
- First line = emotional hook that creates FOMO
- Add call-to-action: "Follow for more!", "Comment your reaction!", "Save this!"
- Include 3-5 relevant keywords naturally
- Maximum 150 characters

🏷️ VIRAL TAGS RULES:
- Exactly 5 hashtags
- Mix of: 2 trending tags + 2 niche tags + 1 broad tag
- All lowercase, no spaces
- Use currently trending hashtags

OUTPUT JSON ONLY:
{{
  "title": "viral title here",
  "description": "viral description with CTA",
  "tags": ["viral", "trending", "niche1", "niche2", "broad"]
}}"""
            
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
                    "text": f"""You are an expert YouTube Shorts viral content strategist with 10+ years of experience.

Analyze these video frames and create VIRAL metadata that will EXPLODE on YouTube Shorts.

Channel: {channel_name}
Video: {filename}

🔥 VIRAL TITLE RULES:
- MAXIMUM 50 characters (YouTube cuts off longer titles)
- Use power words: "Insane", "Mind-Blowing", "You Won't Believe", "Secret", "Shocking"
- Create curiosity gap - make them NEED to watch
- NO emojis, NO clickbait lies
- Pattern interrupt - something unexpected

💥 VIRAL DESCRIPTION RULES:
- First line = emotional hook that creates FOMO
- Add call-to-action: "Follow for more!", "Comment your reaction!"
- Include 3-5 relevant keywords naturally
- Maximum 150 characters

🏷️ VIRAL TAGS RULES:
- Exactly 5 hashtags
- Mix of: 2 trending tags + 2 niche tags + 1 broad tag
- All lowercase, no spaces
- Research current viral trends

OUTPUT JSON ONLY:
{{
  "title": "viral title here",
  "description": "viral description with CTA",
  "tags": ["viral", "trending", "niche1", "niche2", "broad"]
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


# Global model cache for Moondream
_moondream_model = None
_moondream_tokenizer = None

def get_moondream_model():
    """Load Moondream model with caching (only loads once)"""
    global _moondream_model, _moondream_tokenizer
    
    if _moondream_model is not None:
        return _moondream_model, _moondream_tokenizer
    
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        print("📥 Loading Moondream vision model (first time only)...", file=sys.stderr)
        
        model_id = "vikhyatk/moondream2"
        revision = "2025-01-09"  # Latest stable version
        
        # Load tokenizer
        _moondream_tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        
        # Load model - use CPU for GitHub Actions compatibility
        _moondream_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        ).to("cpu")
        
        # Set to evaluation mode
        _moondream_model.eval()
        
        print("✅ Moondream model loaded successfully!", file=sys.stderr)
        return _moondream_model, _moondream_tokenizer
        
    except Exception as e:
        print(f"❌ Failed to load Moondream model: {e}", file=sys.stderr)
        return None, None


def analyze_video_with_moondream(video_buffer, filename, channel_name=""):
    """
    Analyze video with local Moondream vision model (runs on CPU)
    FREE - No API costs! Lightweight 1.8B parameter model
    
    Args:
        video_buffer: BytesIO buffer containing video data
        filename: Original filename
        channel_name: Name of the channel for context
        
    Returns:
        dict: {"title": str, "description": str, "tags": list} or None if failed
    """
    try:
        import cv2
        from PIL import Image
        import io
        
        print("🌙 Using local Moondream model for analysis...", file=sys.stderr)
        
        # Load model
        model, tokenizer = get_moondream_model()
        if model is None:
            return None
        
        # Save video to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            video_buffer.seek(0)
            tmp_file.write(video_buffer.read())
            tmp_path = tmp_file.name
        
        try:
            # Extract frames from video
            print(f"🎬 Extracting frames for Moondream analysis...", file=sys.stderr)
            cap = cv2.VideoCapture(tmp_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Get middle frame (best representation)
            middle_pos = total_frames // 2
            cap.set(cv2.CAP_PROP_POS_FRAMES, middle_pos)
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                print("Warning: Could not extract frame from video", file=sys.stderr)
                return None
            
            # Convert BGR to RGB and resize
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb = cv2.resize(frame_rgb, (384, 384))  # Moondream optimal size
            
            # Convert to PIL Image
            pil_image = Image.fromarray(frame_rgb)
            
            # Encode image for model
            encoded_image = model.encode_image(pil_image)
            
            # First, get a description of what's in the video
            description_prompt = "Describe what you see in this image in detail. What is the main subject? What action or scene is shown?"
            description = model.answer_question(encoded_image, description_prompt, tokenizer)
            
            print(f"📝 Moondream description: {description[:100]}...", file=sys.stderr)
            
            # Now generate viral metadata based on the description
            # We'll use simple text processing since Moondream is for vision
            viral_metadata = generate_viral_metadata_from_description(description, channel_name, filename)
            
            return viral_metadata
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        print(f"Error in Moondream analysis: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


def generate_viral_metadata_from_description(description, channel_name="", filename=""):
    """
    Generate viral YouTube Shorts metadata from a video description
    Uses pattern matching and templates for viral content
    
    Args:
        description: Text description of the video content
        channel_name: Name of the channel for context
        filename: Original filename for hints
        
    Returns:
        dict: {"title": str, "description": str, "tags": list, "category_id": str}
    """
    import re
    
    description_lower = description.lower()
    
    # Power words for viral titles
    power_words = ["INSANE", "INCREDIBLE", "UNBELIEVABLE", "SHOCKING", "AMAZING", 
                   "MIND-BLOWING", "EPIC", "LEGENDARY", "WILD", "CRAZY"]
    
    # Detect content category and generate appropriate metadata
    if any(word in description_lower for word in ["cat", "dog", "pet", "animal", "puppy", "kitten"]):
        category = "animals"
        hooks = ["This Will Melt Your Heart! 🥺", "Wait For It... 😱", "I Can't Stop Watching! 🔥"]
        tags = ["animals", "pets", "cute", "funny", "viral", "shorts"]
        category_id = "15"  # Pets & Animals
        
    elif any(word in description_lower for word in ["food", "cook", "eat", "recipe", "delicious", "chef"]):
        category = "food"
        hooks = ["You NEED To Try This! 🤤", "Food Hack That Changed My Life!", "Wait Until You See This! 😋"]
        tags = ["food", "cooking", "recipe", "foodie", "viral", "shorts"]
        category_id = "26"  # Howto & Style
        
    elif any(word in description_lower for word in ["game", "gaming", "play", "player", "gamer", "video game"]):
        category = "gaming"
        hooks = ["This Play Was INSANE! 🎮", "Watch This Clutch! 🔥", "They Didn't See This Coming! 😱"]
        tags = ["gaming", "gamer", "gameplay", "epic", "viral", "shorts"]
        category_id = "20"  # Gaming
        
    elif any(word in description_lower for word in ["satisfying", "oddly", "smooth", "perfect", "asmr"]):
        category = "satisfying"
        hooks = ["So Satisfying To Watch! 😌", "I Could Watch This Forever!", "Pure Satisfaction! ✨"]
        tags = ["satisfying", "oddlysatisfying", "asmr", "relaxing", "viral", "shorts"]
        category_id = "24"  # Entertainment
        
    elif any(word in description_lower for word in ["funny", "laugh", "comedy", "hilarious", "joke"]):
        category = "comedy"
        hooks = ["I Can't Stop Laughing! 😂", "This Is Too Funny!", "Wait For The End! 🤣"]
        tags = ["funny", "comedy", "laugh", "humor", "viral", "shorts"]
        category_id = "23"  # Comedy
        
    elif any(word in description_lower for word in ["tech", "gadget", "phone", "computer", "device", "robot"]):
        category = "tech"
        hooks = ["This Tech Is From The Future! 🤯", "You Won't Believe This Gadget!", "Game Changer! 🔥"]
        tags = ["tech", "gadgets", "technology", "innovation", "viral", "shorts"]
        category_id = "28"  # Science & Technology
        
    elif any(word in description_lower for word in ["car", "drive", "vehicle", "race", "speed", "motor"]):
        category = "cars"
        hooks = ["This Car Is INSANE! 🏎️", "Listen To That Engine! 🔥", "Pure Power! 💪"]
        tags = ["cars", "automotive", "racing", "supercar", "viral", "shorts"]
        category_id = "2"  # Autos & Vehicles
        
    elif any(word in description_lower for word in ["fitness", "workout", "gym", "exercise", "muscle", "training"]):
        category = "fitness"
        hooks = ["Try This Workout! 💪", "Fitness Hack That Works!", "Transform Your Body! 🔥"]
        tags = ["fitness", "workout", "gym", "exercise", "motivation", "shorts"]
        category_id = "17"  # Sports
        
    elif any(word in description_lower for word in ["beauty", "makeup", "skincare", "fashion", "style", "outfit"]):
        category = "beauty"
        hooks = ["This Changed Everything! ✨", "Beauty Secret Revealed!", "You Need This! 💅"]
        tags = ["beauty", "makeup", "skincare", "fashion", "style", "shorts"]
        category_id = "26"  # Howto & Style
        
    else:
        # Default/general content
        category = "general"
        hooks = ["You Have To See This! 🔥", "Wait For It... 😱", "This Is INCREDIBLE! 🤯"]
        tags = ["viral", "trending", "amazing", "mustwatch", "shorts"]
        category_id = "24"  # Entertainment
    
    import random
    
    # Generate title
    hook = random.choice(hooks)
    power_word = random.choice(power_words)
    
    # Create a short summary from description (first sentence or 50 chars)
    summary = description.split('.')[0][:50].strip()
    if len(summary) > 30:
        summary = summary[:30] + "..."
    
    # Final title (max 100 chars for YouTube)
    title = f"{hook}"
    if len(title) < 60:
        title = f"{power_word}! {hook}"
    
    # Generate description with CTAs
    full_description = f"""{description[:200]}

🔥 {hook}

👆 WATCH TILL THE END!
💬 Comment what you think!
❤️ Like if you enjoyed this!
🔔 Follow for more!

#shorts #{category} #viral #trending #fyp"""
    
    return {
        "title": title[:100],
        "description": full_description[:5000],
        "tags": tags + ["shorts", "viral", "trending", "fyp"],
        "category_id": category_id
    }


def analyze_video_with_together(video_buffer, filename, channel_name=""):
    """
    Analyze video with Together AI's LLaVA model (LLaMA + Vision)
    FREE $25 credits - very generous quota!
    
    Args:
        video_buffer: BytesIO buffer containing video data
        filename: Original filename
        channel_name: Name of the channel for context
        
    Returns:
        dict: {"title": str, "description": str, "tags": list} or None if failed
    """
    if not TOGETHER_API_KEY:
        print("Warning: TOGETHER_API_KEY not set, cannot use Together AI fallback", file=sys.stderr)
        return None
    
    try:
        import cv2
        import base64
        import requests
        
        # Save video to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            video_buffer.seek(0)
            tmp_file.write(video_buffer.read())
            tmp_path = tmp_file.name
        
        try:
            # Extract frames from video
            print(f"🎬 Extracting frames for LLaVA analysis...", file=sys.stderr)
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
            
            # Build prompt for LLaVA
            print(f"🦙 Analyzing with LLaVA (LLaMA Vision)...", file=sys.stderr)
            
            prompt = f"""You are an expert YouTube Shorts viral content strategist with 10+ years of experience.

Analyze these video frames and create VIRAL metadata that will EXPLODE on YouTube Shorts.

Channel: {channel_name}
Video: {filename}

🔥 VIRAL TITLE RULES:
- MAXIMUM 50 characters (YouTube cuts off longer titles)
- Use power words: "Insane", "Mind-Blowing", "You Won't Believe", "Secret", "Shocking"
- Create curiosity gap - make them NEED to watch
- NO emojis, NO clickbait lies
- Pattern interrupt - something unexpected

💥 VIRAL DESCRIPTION RULES:
- First line = emotional hook that creates FOMO
- Add call-to-action: "Follow for more!", "Comment your reaction!"
- Include 3-5 relevant keywords naturally
- Maximum 150 characters

🏷️ VIRAL TAGS RULES:
- Exactly 5 hashtags
- Mix of: 2 trending tags + 2 niche tags + 1 broad tag
- All lowercase, no spaces
- Research current viral trends

OUTPUT JSON ONLY:
{{
  "title": "viral title here",
  "description": "viral description with CTA",
  "tags": ["viral", "trending", "niche1", "niche2", "broad"]
}}"""

            # Use only the middle frame (most representative) for LLaVA
            middle_frame = encoded_frames[len(encoded_frames) // 2]
            
            # Call Together AI API
            response = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {TOGETHER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama/Llama-Vision-Free",  # FREE LLaVA model
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{middle_frame}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7
                },
                timeout=60
            )
            
            if response.status_code == 429:
                print("⚠️ Together AI rate limited", file=sys.stderr)
                return "QUOTA_EXCEEDED"
            
            response.raise_for_status()
            result = response.json()
            
            # Parse response
            response_text = result["choices"][0]["message"]["content"].strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
            
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group()
            
            metadata = json.loads(response_text)
            
            # Validate and clean metadata
            title = metadata.get("title", "")[:100]
            description = metadata.get("description", "")[:5000]
            tags = metadata.get("tags", [])[:15]
            
            print(f"✅ LLaVA Generated: {title}", file=sys.stderr)
            
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
        error_msg = str(e).lower()
        if "429" in error_msg or "rate" in error_msg or "quota" in error_msg:
            print(f"⚠️ Together AI quota exceeded: {e}", file=sys.stderr)
            return "QUOTA_EXCEEDED"
        print(f"Error in Together AI analysis: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


def analyze_video_with_ai(video_buffer, filename, channel_name=""):
    """
    Analyze video with AI - tries multiple providers with fallbacks
    Priority: Moondream (local/free) -> Gemini -> Together AI -> OpenAI
    
    Args:
        video_buffer: BytesIO buffer containing video data
        filename: Original filename
        channel_name: Name of the channel for context
        
    Returns:
        dict: {"title": str, "description": str, "tags": list} or None if all failed
    """
    # Check if local model is preferred (set USE_LOCAL_MODEL=true to prefer local)
    use_local_first = os.environ.get("USE_LOCAL_MODEL", "true").lower() == "true"
    
    if use_local_first:
        # Try local Moondream first (FREE, no API costs!)
        print("🌙 Trying local Moondream model first...", file=sys.stderr)
        video_buffer.seek(0)
        result = analyze_video_with_moondream(video_buffer, filename, channel_name)
        if result is not None:
            return result
        print("⚠️ Local model failed, trying cloud APIs...", file=sys.stderr)
    
    # Try Gemini (20 free/day)
    if GEMINI_API_KEY:
        video_buffer.seek(0)
        result = analyze_video_with_gemini(video_buffer, filename, channel_name)
        if result == "QUOTA_EXCEEDED":
            print("🔄 Gemini quota exceeded, trying next...", file=sys.stderr)
        elif result is not None:
            return result
    
    # Try Together AI (LLaVA) - FREE $25 credits
    if TOGETHER_API_KEY:
        print("🦙 Using Together AI (LLaVA) for analysis...", file=sys.stderr)
        video_buffer.seek(0)
        result = analyze_video_with_together(video_buffer, filename, channel_name)
        if result == "QUOTA_EXCEEDED":
            print("🔄 Together AI quota exceeded, trying OpenAI...", file=sys.stderr)
        elif result is not None:
            return result
    
    # Try OpenAI as last resort
    if OPENAI_API_KEY:
        print("🤖 Using OpenAI for analysis...", file=sys.stderr)
        video_buffer.seek(0)
        result = analyze_video_with_openai(video_buffer, filename, channel_name)
        if result is not None:
            return result
    
    # If local model wasn't tried first, try it now as last resort
    if not use_local_first:
        print("🌙 Trying local Moondream model as fallback...", file=sys.stderr)
        video_buffer.seek(0)
        result = analyze_video_with_moondream(video_buffer, filename, channel_name)
        if result is not None:
            return result
    
    # All AI providers failed
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
            
            # Check for subfolders first
            subfolders = get_subfolders_from_drive(drive_service, folder_id)
            
            if subfolders:
                # Count videos in all subfolders
                for subfolder in subfolders:
                    page_token = None
                    while True:
                        results = drive_service.files().list(
                            q=f"'{subfolder['id']}' in parents and mimeType contains 'video/' and trashed = false",
                            pageSize=100,
                            pageToken=page_token,
                            fields="nextPageToken, files(id)"
                        ).execute()
                        
                        total += len(results.get("files", []))
                        page_token = results.get("nextPageToken")
                        
                        if not page_token:
                            break
            else:
                # No subfolders, count videos in main folder
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
            
            # Check for subfolders first
            subfolders = get_subfolders_from_drive(drive_service, folder_id)
            folders_to_scan = []
            
            if subfolders:
                # Scan all subfolders
                for sf in subfolders:
                    folders_to_scan.append({"id": sf["id"], "name": sf["name"]})
            else:
                # No subfolders, scan main folder
                folders_to_scan.append({"id": folder_id, "name": "main"})
            
            for folder in folders_to_scan:
                results = drive_service.files().list(
                    q=f"'{folder['id']}' in parents and mimeType contains 'video/' and trashed = false",
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
                        "subfolder": folder["name"],
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
    
    # Use subfolder rotation to get next video
    print(f"🔄 Getting next video with subfolder rotation for {target_channel['name']}...", file=sys.stderr)
    file, subfolder_name = get_next_video_with_subfolder_rotation(
        drive_service, 
        folder_id, 
        target_channel["id"], 
        uploaded_ids, 
        uploaded_titles
    )
    
    if not file:
        return {"success": False, "error": "No videos left to upload (all subfolders exhausted)"}
    
    file_id = file["id"]
    file_name = file["name"]
    mime_type = file.get("mimeType", "video/mp4")
    
    print(f"📹 Selected: {file_name} from subfolder: {subfolder_name}", file=sys.stderr)
    
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
