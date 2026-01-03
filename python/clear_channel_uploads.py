"""
Script to clear uploaded video history for a specific channel.
This allows re-uploading videos to a channel after changing its Drive folder.
"""
import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://ajyadodiya2003_db_user:AnPvBaCyJBI3XFp5@yt-automation.q12aqvq.mongodb.net/yt_automation?retryWrites=true&w=majority&appName=YT-Automation')

def clear_channel_uploads(channel_id):
    """Clear uploaded video history for a specific channel"""
    client = MongoClient(MONGODB_URI)
    db = client['yt_automation']
    
    # Delete all uploaded videos for this channel
    result = db.uploaded_videos.delete_many({"channel_id": channel_id})
    
    print(f"✅ Deleted {result.deleted_count} uploaded video records for channel: {channel_id}")
    
    # Show remaining uploads by channel
    print("\nRemaining uploads by channel:")
    pipeline = [
        {"$group": {"_id": "$channel_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    for doc in db.uploaded_videos.aggregate(pipeline):
        channel = doc['_id'] or 'unknown'
        count = doc['count']
        print(f"  - {channel}: {count} videos")
    
    client.close()

def clear_all_uploads():
    """Clear ALL uploaded video history (WARNING: will allow re-uploading everything)"""
    client = MongoClient(MONGODB_URI)
    db = client['yt_automation']
    
    result = db.uploaded_videos.delete_many({})
    
    print(f"⚠️  DELETED ALL {result.deleted_count} uploaded video records!")
    
    client.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python clear_channel_uploads.py channel_1    # Clear uploads for channel_1")
        print("  python clear_channel_uploads.py channel_2    # Clear uploads for channel_2")
        print("  python clear_channel_uploads.py ALL          # Clear ALL uploads (WARNING!)")
        sys.exit(1)
    
    target = sys.argv[1]
    
    if target == "ALL":
        confirm = input("⚠️  This will delete ALL uploaded video history. Type 'yes' to confirm: ")
        if confirm.lower() == "yes":
            clear_all_uploads()
        else:
            print("Cancelled.")
    else:
        clear_channel_uploads(target)
