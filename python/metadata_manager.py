import os
import json
from typing import Dict, List, Optional
from pymongo import MongoClient
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
CHANNELS_CONFIG_FILE = os.path.join(SCRIPT_DIR, "channels_config.json")

class MetadataGenerator:
    """Generate unique video metadata from CSV data"""
    
    def __init__(self):
        self.mongo_uri = os.environ.get("MONGO_URI")
        self.channels_config = self.load_channels_config()
    
    def get_mongo_db(self):
        """Get MongoDB database connection"""
        if not self.mongo_uri:
            return None
        try:
            client = MongoClient(self.mongo_uri)
            return client.yt_automation
        except Exception as e:
            print(f"MongoDB connection error: {e}")
            return None
        
    def load_channels_config(self) -> dict:
        """Load multi-channel configuration from MongoDB or file"""
        # Try MongoDB first - read from 'channels' collection (where dashboard saves)
        db = self.get_mongo_db()
        if db is not None:
            try:
                # Read from channels collection directly
                channels_cursor = db.channels.find({})
                channels = []
                for doc in channels_cursor:
                    # Map MongoDB field names to expected format
                    channel = {
                        "id": doc.get("channel_id", ""),
                        "name": doc.get("channel_name", ""),
                        "drive_folder_id": doc.get("drive_folder_id", ""),
                        "youtube_account": doc.get("channel_id", ""),  # channel_id is like "account1"
                        "enabled": doc.get("enabled", True),
                        "title_template": doc.get("title_template", "{trending_title}"),
                        "description_template": doc.get("description_template", "{trending_description}"),
                        "tags": doc.get("tags", []),
                        "category_id": doc.get("category_id", "22"),
                        "categories": doc.get("categories", []),
                        "use_ai_metadata": True
                    }
                    channels.append(channel)
                
                if channels:
                    # Load youtube_accounts from channels_config if available
                    config_doc = db.channels_config.find_one({"_id": "main_config"})
                    youtube_accounts = config_doc.get("youtube_accounts", {}) if config_doc else {}
                    
                    # If no youtube_accounts in DB, load from local file
                    if not youtube_accounts and os.path.exists(CHANNELS_CONFIG_FILE):
                        with open(CHANNELS_CONFIG_FILE, 'r') as f:
                            local_config = json.load(f)
                            youtube_accounts = local_config.get("youtube_accounts", {})
                    
                    return {
                        "channels": channels,
                        "youtube_accounts": youtube_accounts
                    }
            except Exception as e:
                print(f"Failed to load channels from MongoDB: {e}")
        
        # Fallback to file
        if os.path.exists(CHANNELS_CONFIG_FILE):
            with open(CHANNELS_CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {"channels": [], "youtube_accounts": {}}
    
    def save_channels_config(self, config: dict):
        """Save multi-channel configuration to MongoDB and file"""
        # Save to MongoDB
        db = self.get_mongo_db()
        if db is not None:
            try:
                db.channels_config.update_one(
                    {"_id": "main_config"},
                    {
                        "$set": {
                            "channels": config.get("channels", []),
                            "youtube_accounts": config.get("youtube_accounts", {}),
                            "updated_at": datetime.now()
                        }
                    },
                    upsert=True
                )
            except Exception as e:
                print(f"Failed to save channels to MongoDB: {e}")
        
        # Also save to file as backup
        with open(CHANNELS_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    

    
    def get_channel_by_id(self, channel_id: str) -> Optional[dict]:
        """Get channel configuration by ID"""
        for channel in self.channels_config.get("channels", []):
            if channel["id"] == channel_id:
                return channel
        return None
    
    def get_enabled_channels(self) -> List[dict]:
        """Get all enabled channels"""
        return [ch for ch in self.channels_config.get("channels", []) if ch.get("enabled", True)]
    
    def get_channel_for_folder(self, folder_id: str) -> Optional[dict]:
        """Find channel associated with a Drive folder ID"""
        for channel in self.channels_config.get("channels", []):
            if channel.get("drive_folder_id") == folder_id and channel.get("enabled", True):
                return channel
        return None
    
    def generate_metadata(self, channel_id: str, video_filename: str = None) -> Dict[str, any]:
        """Generate metadata for a video based on channel configuration"""
        channel = self.get_channel_by_id(channel_id)
        if not channel:
            return self._get_fallback_metadata(video_filename)
        
        return self._generate_static_metadata(channel, video_filename)
    

    

    
    def _generate_static_metadata(self, channel: dict, filename: str = None) -> Dict:
        """Generate metadata using channel templates or filename"""
        # Get templates from channel config
        templates = channel.get("templates", {})
        title_template = templates.get("title", "Amazing Video #Shorts")
        description_template = templates.get("description", "Check out this amazing video!")
        
        # If templates contain placeholders, generate from filename
        if "{trending_title}" in title_template or "{trending_description}" in description_template:
            # Generate title from filename
            if filename:
                # Clean up filename: remove extension, underscores, numbers
                clean_name = filename.rsplit('.', 1)[0]  # Remove extension
                clean_name = clean_name.replace('_', ' ').replace('-', ' ')
                # Remove leading numbers/timestamps
                import re
                clean_name = re.sub(r'^\d+\s*', '', clean_name)
                clean_name = clean_name.strip()
                
                if clean_name:
                    title = f"{clean_name[:55]} #Shorts"
                else:
                    title = f"{channel.get('name', 'Amazing Video')} #Shorts"
            else:
                title = f"{channel.get('name', 'Amazing Video')} #Shorts"
            
            channel_name = channel.get('name', '')
            description = f"{title}\n\n#shorts #viral #trending"
        else:
            title = title_template
            description = description_template
        
        # Get default tags from channel or use fallback
        tags = channel.get("default_tags", ["shorts", "viral", "trending"])
        
        return {
            "title": title[:100],  # YouTube max
            "description": description[:5000],  # YouTube max
            "tags": tags,
            "category": "Entertainment"
        }
    
    def _get_fallback_metadata(self, filename: str = None) -> Dict:
        """Fallback metadata when no channel is configured"""
        if filename:
            # Generate title from filename
            import re
            clean_name = filename.rsplit('.', 1)[0]
            clean_name = clean_name.replace('_', ' ').replace('-', ' ')
            clean_name = re.sub(r'^\d+\s*', '', clean_name).strip()
            
            if clean_name:
                title = f"{clean_name[:55]} #Shorts"
            else:
                title = "Amazing Video #Shorts"
        else:
            title = "Amazing Video #Shorts"
        
        return {
            "title": title,
            "description": f"{title}\n\n#shorts #viral #trending",
            "tags": ["shorts", "viral", "trending"],
            "category": "Entertainment",
            "source_csv": None
        }
    

    



# Singleton instance
_metadata_generator = None

def get_metadata_generator() -> MetadataGenerator:
    """Get singleton metadata generator instance"""
    global _metadata_generator
    if _metadata_generator is None:
        _metadata_generator = MetadataGenerator()
    return _metadata_generator
