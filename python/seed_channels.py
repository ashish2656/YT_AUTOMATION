"""
Script to seed MongoDB with channel configurations from channels_config.json.
Run this once to sync channels to MongoDB.
"""
import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection - password is URL encoded
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://ajyadodiya2003_db_user:AnPvBaCyJBI3XFp5@yt-automation.q12aqvq.mongodb.net/yt_automation?retryWrites=true&w=majority&appName=YT-Automation')

def extract_folder_id(url_or_id):
    """Extract folder ID from Google Drive URL or return as-is if already an ID."""
    if not url_or_id:
        return ""
    if 'drive.google.com' in url_or_id:
        # Extract from URL like https://drive.google.com/drive/folders/XXXXX
        if '/folders/' in url_or_id:
            return url_or_id.split('/folders/')[-1].split('?')[0].split('/')[0]
    return url_or_id

def seed_channels():
    # Load from channels_config.json
    config_path = os.path.join(os.path.dirname(__file__), 'channels_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    client = MongoClient(MONGODB_URI)
    db = client['yt_automation']
    channels_collection = db['channels']
    
    # Clear existing channels
    channels_collection.delete_many({})
    
    # Convert channels to MongoDB format
    channel_docs = []
    for ch in config.get('channels', []):
        channel_docs.append({
            "channel_id": ch.get('youtube_account', ch.get('id')),
            "channel_name": ch.get('name', ''),
            "drive_folder_id": extract_folder_id(ch.get('drive_folder_id', '')),
            "drive_folder_url": ch.get('drive_folder_id', ''),
            "enabled": ch.get('enabled', True),
            "title_template": ch.get('templates', {}).get('title', '{trending_title}'),
            "description_template": ch.get('templates', {}).get('description', '{trending_description}'),
            "tags": ["shorts"],
            "category_id": "22",
            "categories": ch.get('categories', [])
        })
    
    # Insert channels
    if channel_docs:
        result = channels_collection.insert_many(channel_docs)
        print(f"✅ Inserted {len(result.inserted_ids)} channels into MongoDB")
    
    # Print channels
    print("\nChannels in database:")
    for ch in channels_collection.find({}):
        print(f"  - {ch['channel_id']}: {ch['channel_name']}")
        print(f"    Drive Folder: {ch['drive_folder_id']}")
        print(f"    Enabled: {ch['enabled']}")
    
    client.close()

if __name__ == "__main__":
    seed_channels()
