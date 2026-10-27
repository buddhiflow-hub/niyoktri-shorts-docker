# ⚡ Niyoktri Shorts Factory (Dockerized Edition) ⚡

An autonomous, GPU-free, Docker-ready pipeline for creating and auto-publishing high-retention vertical Short-form videos (YouTube Shorts, Instagram Reels, TikTok).

## 🚀 Key Features

- **Ultrafast Voiceover**: Powered by **Microsoft Edge-TTS** (async neural speech synthesis, 0s GPU wait, natural human inflections).
- **Dual Stock Footage Harvester**: Automated video search and download with smart fallback:
  - **Pexels Video API** (Primary HD/4K vertical footage)
  - **Pixabay Video API** (Fallback nature and motion clips)
  - **Synthetic Gradient Motion Engine** (Emergency fallback canvas if APIs are offline)
- **Kinetic Gold Glow Subtitles**: 
  - Word-level synchronization using **faster-whisper** (CTranslate2 INT8 CPU inference).
  - High-impact `.ass` subtitles with active glowing gold word animation (`&H0022FFFF&` bounce punch-in `\t(0,80,\fscx112\fscy112)`).
- **FFmpeg Master Assembly**:
  - Automatic 9:16 vertical crop and smart pacing (scale & center crop).
  - Background music sidechain ducking (-15dB speech suppression).
  - Hardcoded burnt subtitles with custom typography support.
- **Autonomous Multi-Platform Publishing**:
  - YouTube Data API v3 scheduler (`publishAt` scheduled uploads).
  - Automatic SEO hashtagging (`#Shorts`, series tags).
  - Automated playlist indexing.
  - Persistent SQLite history and quota tracking.

---

## 📂 Architecture & Directory Structure

```text
niyoktri-shorts-docker/
├── Dockerfile                  # Lightweight Debian Bookworm + FFmpeg + pre-cached Whisper
├── docker-compose.yml          # Container configuration with mounted storage volume
├── .env.example                # API credentials template
├── config.yaml                 # Central customization (voice, fonts, margins, ducking)
├── entrypoint.sh               # Container initialization script
├── requirements.txt            # Python dependencies
├── assets/
│   ├── fonts/                  # Custom TrueType fonts (Montserrat-ExtraBold, etc.)
│   └── music/                  # Curated background music loops
├── src/
│   ├── main.py                 # Unified CLI and pipeline orchestrator
│   ├── core/
│   │   ├── config_loader.py    # YAML and environment loader
│   │   ├── db.py               # SQLite state and history manager
│   │   └── models.py           # Pydantic data contracts
│   ├── tts/
│   │   └── edge_voice.py       # Asynchronous Edge-TTS engine
│   ├── stock/
│   │   ├── pexels_api.py       # Pexels Video API client
│   │   ├── pixabay_api.py      # Pixabay Video API client
│   │   └── video_processor.py  # 9:16 vertical formatting and pacing
│   ├── subtitles/
│   │   ├── aligner.py          # faster-whisper word-level aligner
│   │   └── ass_builder.py      # Kinetic Gold Glow ASS subtitle generator
│   ├── composer/
│   │   └── ffmpeg_engine.py    # FFmpeg concat, audio ducking & subtitle burner
│   ├── publisher/
│   │   ├── base.py             # Abstract publisher
│   │   └── youtube.py          # YouTube Data API v3 scheduler
│   └── scheduler/
│       └── cron_task.py        # Automated recurring publisher daemon
└── storage/                    # Persistent host mount
    ├── input/                  # Script JSON and markdown queues
    ├── output/                 # Final rendered 1080x1920 MP4s
    ├── cache/                  # Downloaded videos, audio and whisper models
    └── secrets/                # YouTube OAuth credentials
```

---

## 🛠️ Quick Start Guide

### 1. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your API keys:
- `PEXELS_API_KEY`: Get a free key at [pexels.com/api](https://www.pexels.com/api/)
- `PIXABAY_API_KEY`: Get a free key at [pixabay.com/api/docs](https://pixabay.com/api/docs/)
- `YOUTUBE_CLIENT_SECRET_FILE`: Path to Google Cloud OAuth client secret.

### 2. Build & Run with Docker Compose

Build the container image:
```bash
docker compose build
```

Run a smoke test:
```bash
docker compose run --rm shorts-factory python src/main.py --mode test
```

Render a specific episode:
```bash
docker compose run --rm shorts-factory python src/main.py --mode single --script /app/storage/input/sample_episode.json
```

Render and automatically upload/schedule on YouTube:
```bash
docker compose run --rm shorts-factory python src/main.py --mode single --script /app/storage/input/sample_episode.json --publish
```

Start the 24/7 autonomous scheduling daemon:
```bash
docker compose up -d
```

---

## 🧪 Local Execution (Without Docker)

If you prefer running directly in a local Python environment (e.g., Python 3.10+):

1. Install system FFmpeg with `libass` support.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run smoke test:
   ```bash
   python src/main.py --mode test
   ```

---

## 🎬 Customizing Subtitles & Voices

In [config.yaml](file:///c:/Users/LENOVO/Desktop/Niyoktri/niyoktri-shorts-docker/config.yaml):
- **Voice**: Set `tts.default_voice` to `en-US-ChristopherNeural`, `en-US-GuyNeural`, `en-GB-RyanNeural`, `hi-IN-MadhurNeural`, etc.
- **Subtitle Color**: Modify `subtitles.active_color` (e.g. `&H0022FFFF` for Gold, `&H0000FFFF` for Yellow, `&H00FF00FF` for Neon Magenta).
- **BGM Ducking**: Tune `audio.bgm_volume` and `audio.bgm_duck_db`.
