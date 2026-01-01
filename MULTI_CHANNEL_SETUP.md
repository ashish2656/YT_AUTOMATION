# Multi-Channel YouTube Automation - Setup Guide

## 🎯 Overview

Your YouTube automation system now supports **multiple channels with dynamic metadata generation**! Each channel can be linked to a different Google Drive folder, and videos will automatically get unique titles, descriptions, and tags based on 48,081+ trending content data points from CSV files.

## 🚀 What's New

### 1. **Multi-Channel Management**
- Create unlimited YouTube channel configurations
- Each channel can have its own Google Drive folder
- Enable/disable channels individually
- Customize metadata templates per channel

### 2. **CSV-Driven Dynamic Metadata**
- **48,081 trending videos** from TikTok/YouTube Shorts analyzed
- Automatically generates unique titles, descriptions, and tags
- Never repeats the same metadata combination
- Uses real trending data for better engagement

### 3. **Channel-Folder Correlation**
- Map specific Drive folders to specific channels
- Videos from each folder get channel-specific metadata
- One YouTube OAuth token works for all channels
- Automatic channel detection based on folder ID

## 📁 File Structure

```
YT_AUTOMATION/
├── python/
│   ├── automation.py           # Core automation script (updated)
│   ├── metadata_manager.py     # NEW: Metadata generation engine
│   ├── channels_config.json    # NEW: Multi-channel configuration
│   └── requirements.txt
├── data/
│   ├── youtube_shorts_tiktok_trends_2025.csv    # 48K+ trending videos
│   ├── top_hashtags_2025.csv                    # Top hashtags
│   └── country_platform_summary_2025.csv        # Platform stats
├── src/app/
│   ├── page.tsx               # Dashboard UI (updated with Channels tab)
│   └── api/
│       ├── channels/route.ts  # NEW: Channel management API
│       └── metadata/route.ts  # NEW: Metadata generation API
```

## 🎮 How to Use

### Step 1: Open the Channels Manager

1. Go to your dashboard at `http://localhost:3000`
2. Click the **Folder icon** 📁 in the top-right corner
3. Click **"New Channel"**

### Step 2: Create a Channel

Fill in the following fields:

- **Channel Name**: e.g., "Gaming Channel", "Lifestyle Vlogs"
- **Google Drive Folder ID**: Get this from your Drive folder URL
  - Example URL: `https://drive.google.com/drive/folders/1abc123xyz...`
  - Folder ID: `1abc123xyz...`
- **Categories**: Gaming, Entertainment, Comedy (comma-separated)
- **Title Template**: Use variables like:
  - `{trending_title}` - A trending title from CSV data
  - `{hashtags}` - Top trending hashtags
  - `{category}` - Video category
- **Description Template**: Use variables like:
  - `{trending_description}` - A trending description
  - `{hashtags}` - Auto-inserted hashtags

### Step 3: Configure Multiple Channels

Example setup:

#### Channel 1: Gaming
```
Name: Gaming Channel
Folder ID: 1abc123gaming
Categories: Gaming, Esports, FPS
Title: {trending_title} 🎮 #gaming
Description: {trending_description}

🎮 Follow for more gaming content!
#gaming #shorts {hashtags}
```

#### Channel 2: Lifestyle
```
Name: Lifestyle Vlogs
Folder ID: 1xyz789lifestyle
Categories: Lifestyle, Daily Vlogs, Travel
Title: {trending_title} ✨
Description: {trending_description}

✨ Daily lifestyle content
{hashtags} #lifestyle #shorts
```

### Step 4: Upload Videos

1. Place videos in the respective Drive folders
2. Click **"Upload Next Video"** on the dashboard
3. The system will:
   - Detect which channel the video belongs to (based on folder ID)
   - Generate unique metadata from CSV trending data
   - Upload with channel-specific title/description/tags
   - Track the metadata to avoid duplicates

## 🧠 How Metadata Generation Works

### The Smart Algorithm

1. **Channel Detection**: System identifies which channel the video belongs to based on Drive folder ID
2. **CSV Data Loading**: Loads 48K+ trending videos with titles, descriptions, hashtags, engagement metrics
3. **Category Filtering**: Filters CSV data by channel categories (e.g., "Gaming" channel only gets gaming content)
4. **Uniqueness Check**: Ensures no title+description combination is ever reused
5. **Template Expansion**: Replaces `{trending_title}` with actual trending title from CSV
6. **Hashtag Injection**: Adds top performing hashtags from trends data

### Available CSV Data

Your system has access to:

- **48,081 trending videos** with:
  - Titles optimized for engagement
  - Descriptions that perform well
  - Top hashtags by category
  - View counts, like counts, comment counts
  - Platform-specific trends (TikTok, YouTube Shorts)

## 🔧 API Endpoints

### Channels Management

```bash
# List all channels
GET /api/channels

# Create channel
POST /api/channels
{
  "action": "create",
  "channelData": {
    "name": "Gaming Channel",
    "drive_folder_id": "1abc123...",
    "categories": ["Gaming", "Entertainment"],
    "templates": {
      "title": "{trending_title}",
      "description": "{trending_description}\n\n#shorts"
    }
  }
}

# Update channel
POST /api/channels
{
  "action": "update",
  "channelId": "channel_1",
  "channelData": { ... }
}

# Delete channel
POST /api/channels
{
  "action": "delete",
  "channelId": "channel_1"
}

# Toggle channel
POST /api/channels
{
  "action": "toggle",
  "channelId": "channel_1"
}
```

### Metadata Generation

```bash
# Get trending data
GET /api/metadata

# Generate metadata for specific video
POST /api/metadata
{
  "channel_id": "channel_1",
  "filename": "video.mp4"
}
```

## 🎨 Template Variables

Use these in your title and description templates:

| Variable | Description | Example |
|----------|-------------|---------|
| `{trending_title}` | A trending title from CSV data | "POV: When the impostor is sus 😂" |
| `{trending_description}` | A trending description | "This is so relatable! 😭💀" |
| `{hashtags}` | Top 3-5 trending hashtags | "#fyp #viral #trending" |
| `{category}` | Video category | "Gaming" |
| `{filename}` | Original filename | "video_001.mp4" |

## 📊 Benefits

### Before (Single Channel)
- ❌ One static title for all videos
- ❌ Same description every time
- ❌ Manual tag management
- ❌ Can't manage multiple channels

### After (Multi-Channel + Dynamic Metadata)
- ✅ Unique title for every video
- ✅ Trending descriptions from real data
- ✅ Automatic hashtag optimization
- ✅ Manage unlimited channels
- ✅ Channel-specific branding
- ✅ No duplicate content

## 🛠️ Technical Details

### Python Commands

```bash
# List channels
python3 automation.py channels list

# Generate metadata
python3 automation.py metadata generate channel_1 video.mp4

# Get trending data
python3 automation.py metadata trending 20
```

### MongoDB Schema

Videos are now tracked with:
```json
{
  "drive_file_id": "...",
  "file_name": "video.mp4",
  "youtube_video_id": "...",
  "youtube_url": "...",
  "channel_id": "channel_1",
  "title": "Actual title used",
  "description": "Actual description used",
  "tags": ["tag1", "tag2"],
  "uploaded_at": "2025-01-..."
}
```

## 🚨 Important Notes

1. **Single YouTube Token**: You're using one OAuth token for all channels. This means:
   - All videos go to the same YouTube account
   - Channel names are just organizational labels
   - The token.json file authenticates all uploads

2. **CSV Data Location**: CSV files must be in `/data/` directory
   - `youtube_shorts_tiktok_trends_2025.csv` (main dataset)
   - `top_hashtags_2025.csv` (hashtag trends)
   - `country_platform_summary_2025.csv` (platform stats)

3. **Uniqueness Tracking**: The system prevents duplicate metadata by:
   - Hashing title+description combinations
   - Storing used combinations in memory
   - Automatically finding alternative content if duplicate detected

## 📈 Next Steps

1. **Create your channels** in the dashboard
2. **Link Drive folders** to each channel
3. **Customize templates** for each channel's style
4. **Upload videos** and watch the magic happen! ✨

## 🐛 Troubleshooting

**Q: Videos not uploading?**
- Check Drive folder ID is correct
- Ensure channel is enabled (green "Active" badge)
- Verify token.json exists and is valid

**Q: Same metadata being used?**
- Check CSV files are in `/data/` directory
- Verify categories match CSV data categories
- System will fallback to config if CSV fails

**Q: Can't see channels in dashboard?**
- Refresh the page
- Check browser console for errors
- Verify Python backend is running

## 💡 Pro Tips

1. Use **different categories** for each channel to get diverse content
2. Customize **templates** to match your channel's voice
3. Monitor **trending hashtags** in the Metadata tab
4. **Enable/disable** channels to control which folders are active
5. Use **descriptive names** for easy channel management

---

**Need help?** Check the browser console (F12) or Python terminal for detailed logs.

**Want more features?** This system is built modularly - easy to extend with more CSV data sources, advanced filtering, or multi-account support!
