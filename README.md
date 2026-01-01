# 🎬 YouTube Shorts Automation System

An automated YouTube Shorts upload system with multi-channel support, AI-powered metadata generation, and scheduled uploads.

![Next.js](https://img.shields.io/badge/Next.js-16.1.1-black?logo=next.js)
![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green?logo=mongodb)
![Gemini AI](https://img.shields.io/badge/Gemini-AI-purple?logo=google)

## ✨ Features

- 🎯 **Multi-Channel Support** - Manage unlimited YouTube channels from one dashboard
- 🤖 **AI-Powered Metadata** - Gemini AI analyzes videos and generates viral titles/descriptions
- 📅 **Scheduled Uploads** - Automatic uploads 3x daily at optimal viewing times
- 📁 **Google Drive Integration** - Pull videos directly from your Drive folders
- 📊 **Analytics Dashboard** - Track uploads, pending videos, and channel stats
- 🔄 **OpenAI Fallback** - Automatic fallback to OpenAI when Gemini quota is exceeded

## 🏗️ Architecture

```
+---------------------------+
|    Next.js Frontend       |
|     (Dashboard UI)        |
+-----------+---------------+
            |
            | API Routes
            v
+-----------+---------------+
|     Python Backend        |
|  +-------+ +-------+ +--+ |
|  | Drive | |YouTube| |AI| |
|  |Reader | |Upload | |  | |
|  +-------+ +-------+ +--+ |
+-----------+---------------+
            |
            v
+-----------+---------------+
|      MongoDB Atlas        |
| +--------+ +--------+     |
| |Channels| |Uploaded|     |
| | Config | | Videos |     |
| +--------+ +--------+     |
+---------------------------+
```

## 🚀 Quick Start

### Prerequisites

- Node.js 20+
- Python 3.13+
- MongoDB Atlas account
- Google Cloud Console project with YouTube Data API & Drive API enabled
- Gemini API key (free tier available)

### Installation

```bash
# Clone the repository
git clone https://github.com/ashish2656/YT_AUTOMATION.git
cd YT_AUTOMATION

# Install Node.js dependencies
npm install

# Create Python virtual environment
cd python
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..

# Start development server
npm run dev
```

### Environment Setup

Create `python/.env` file:

```env
# MongoDB Connection
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/yt_automation

# YouTube OAuth Tokens (one per account)
GOOGLE_TOKEN_ACCOUNT1_JSON='{"token": "...", "refresh_token": "...", ...}'
GOOGLE_TOKEN_ACCOUNT2_JSON='{"token": "...", "refresh_token": "...", ...}'
GOOGLE_TOKEN_ACCOUNT3_JSON='{"token": "...", "refresh_token": "...", ...}'
GOOGLE_TOKEN_ACCOUNT4_JSON='{"token": "...", "refresh_token": "...", ...}'

# AI Keys
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key  # Optional fallback
```

### Generate YouTube Tokens

```bash
cd python
python generate_token.py
# Follow the OAuth flow in your browser
# Token will be saved to token_accountX.json
```

## 📱 Dashboard Features

### Channel Management
- Add/edit/delete YouTube channels
- Configure Drive folder for each channel
- Set custom title/description templates
- Enable/disable channels for uploads

### Upload Controls
- **Upload Next** - Upload one video from selected channel
- **Upload All Channels** - Upload one video from each enabled channel
- View upload history and statistics

### AI Metadata Generation
When `use_ai_metadata` is enabled for a channel:
1. Video is analyzed by Gemini AI (or OpenAI fallback)
2. AI generates viral-worthy title (max 60 chars)
3. AI creates SEO-optimized description
4. AI suggests 5 trending hashtags

## ⏰ Scheduled Uploads (Inngest)

Automatic uploads run 3x daily at optimal viewing times:

| Schedule | Time (IST) | Time (UTC) |
|----------|------------|------------|
| Morning  | 8:00 AM    | 2:30 AM    |
| Afternoon| 1:00 PM    | 7:30 AM    |
| Evening  | 8:00 PM    | 2:30 PM    |

**Daily Upload Calculation:**
- 4 channels × 3 uploads = **12 videos/day**

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, Tailwind CSS, Framer Motion |
| Backend | Python 3.13, Google APIs |
| Database | MongoDB Atlas |
| AI | Google Gemini 2.5 Flash, OpenAI GPT-4o-mini |
| Scheduling | Inngest |
| Deployment | Railway |

## 📁 Project Structure

```
YT_AUTOMATION/
├── src/
│   ├── app/
│   │   ├── page.tsx          # Main dashboard
│   │   └── api/
│   │       ├── channels/     # Channel CRUD
│   │       ├── upload/       # Upload endpoint
│   │       ├── stats/        # Statistics
│   │       ├── videos/       # Video list
│   │       └── inngest/      # Scheduled jobs
│   └── inngest/
│       ├── client.ts         # Inngest config
│       └── functions.ts      # Scheduled functions
├── python/
│   ├── automation.py         # Main automation script
│   ├── metadata_manager.py   # Metadata generation
│   ├── generate_token.py     # OAuth token generator
│   └── requirements.txt      # Python dependencies
├── railway.toml              # Railway deployment config
└── nixpacks.toml             # Build configuration
```

## 🚀 Deployment (Railway)

### Step 1: Connect GitHub
1. Go to [railway.app](https://railway.app)
2. Login with GitHub
3. New Project → Deploy from GitHub → Select this repo

### Step 2: Add Environment Variables
Add all variables from `python/.env` to Railway's Variables tab.

### Step 3: Configure Inngest
1. Create account at [inngest.com](https://inngest.com)
2. Get Event Key and Signing Key
3. Add webhook URL: `https://your-app.railway.app/api/inngest`

### Step 4: Deploy
Railway auto-deploys on git push. First deploy takes ~5-10 minutes.

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/channels` | GET | List all channels |
| `/api/channels` | POST | Create/update/delete channel |
| `/api/upload` | POST | Upload video |
| `/api/stats` | GET | Get upload statistics |
| `/api/videos` | GET | List videos from Drive |
| `/api/history` | GET | Upload history |
| `/api/inngest` | POST | Inngest webhook |

## ⚠️ YouTube API Quota

YouTube Data API has a daily quota of ~10,000 units:
- Each upload costs ~1,600 units
- ~6 uploads per day per project

For more uploads, create additional Google Cloud projects.

## 🔒 Security Notes

- Never commit token files to git
- Use environment variables for all secrets
- Tokens are stored securely in MongoDB
- OAuth refresh tokens auto-renew access tokens

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## 📄 License

MIT License - feel free to use for personal or commercial projects.

## 👨‍�� Author

**Ashish Dodiya**
- GitHub: [@ashish2656](https://github.com/ashish2656)

---

⭐ Star this repo if you find it helpful!
