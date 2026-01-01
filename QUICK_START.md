# 🚀 Quick Start - Multi-Channel YouTube Automation

## 30-Second Setup

### 1. Open Dashboard
Visit: **http://localhost:3000**

### 2. Click Folder Icon 📁
Top-right corner → Opens Channels Manager

### 3. Create New Channel
- Name: `My Gaming Channel`
- Folder ID: Get from Google Drive URL
- Categories: `Gaming, Esports`
- Templates: Use defaults or customize

### 4. Upload Videos
- Put videos in your Drive folder
- Click "Upload Next Video"
- System auto-generates unique metadata! ✨

---

## Quick Reference

### Template Variables
```
{trending_title}       → "Epic Gaming Moments 🎮"
{trending_description} → "Watch this insane gameplay!"
{hashtags}            → "#gaming #shorts #viral"
{category}            → "Gaming"
```

### Example Templates

**Gaming Channel:**
```
Title: {trending_title} 🎮 #gaming
Description: {trending_description}

🔥 Follow for daily gaming content!
#gaming #shorts {hashtags}
```

**Lifestyle Channel:**
```
Title: {trending_title} ✨
Description: {trending_description}

💫 Daily inspiration
{hashtags} #lifestyle
```

---

## Where to Get Drive Folder ID

1. Open your Google Drive folder
2. Look at the URL:
   ```
   https://drive.google.com/drive/folders/1abc123xyz...
                                          ^^^^^^^^^^^
                                          This is your ID!
   ```
3. Copy the ID (after `folders/`)
4. Paste into Channel form

---

## Python Commands

```bash
# List channels
python3 automation.py channels list

# Get trending data
python3 automation.py metadata trending 10

# Generate metadata
python3 automation.py metadata generate channel_1 video.mp4
```

---

## Features

✅ Multiple YouTube channels  
✅ Unique metadata per video (48K+ trending data)  
✅ Automatic Drive folder detection  
✅ No duplicate content  
✅ Beautiful glass UI  
✅ Enable/disable channels  
✅ Custom templates  

---

## Need Help?

📖 Read: `MULTI_CHANNEL_SETUP.md` (full guide)  
🔧 Technical: `IMPLEMENTATION_SUMMARY.md`  
🐛 Issues: Check browser console (F12)  

---

**That's it! You're ready to automate! 🎉**
