---
title: SpotNake
emoji: 🎵
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# SpotNake

SpotNake is a production-ready, AI-driven, multi-provider Telegram bot designed for intelligent music curation, intent parsing, semantic user taste profiling, and fast audio retrieval/download.

## Key Features & Architecture
- **Failover AI Router:** Dynamic routing across multiple models (Gemini -> Groq -> Cerebras -> OpenRouter) to guarantee uninterrupted fallback service for intent parsing and natural language interaction.
- **Taste Profile Store:** Semantic taste profiling database targeting MongoDB Atlas using cosine similarity vector embeddings (via NumPy and Google Gemini API).
- **Audio Retrieval & Transcoding Subprocess:** Automatic search and high-speed audio downloading via `yt-dlp` in async subprocesses, optimized metadata tagging using `mutagen`, and conversion/compression via `ffmpeg`.
- **Egress Bypassing & Advanced Networking:** Extended network timeouts and configurable Telegram API base URL redirection to bypass egress locks in restricted container environments like Hugging Face Spaces.
- **Graceful Container Lifecycle:** Explicit event loop signal handling (`SIGTERM`/`SIGINT`) for proper database disconnection, server cleanup, and polling shutdown.

## Requirements
- Python 3.11+
- `ffmpeg` installed on the host machine (handled automatically by the Docker environment).
- A MongoDB Atlas cluster or equivalent MongoDB URI.

## Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/spot-nake.git
   cd spot-nake
   ```

2. **Initialize a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the root directory (refer to `.env.example`):
   ```env
   TELEGRAM_BOT_TOKEN="your-bot-token"
   TELEGRAM_OWNER_ID=123456789
   TELEGRAM_API_URL="https://api.telegram.org/bot"  # Optional: custom endpoint to bypass regional/egress blocks (e.g. https://tapi.jaze.top/bot)
   MONGODB_URI="your-mongodb-connection-string"
   GEMINI_API_KEY="your-gemini-key"
   GROQ_API_KEY="your-groq-key"
   CEREBRAS_API_KEY="your-cerebras-key"
   OPENROUTER_API_KEY="your-openrouter-key"
   ```

5. **Start the application locally:**
   ```bash
   python3 -m bot.main
   ```

## Docker & Deployment

A Docker setup is provided for deployment.
To build and run locally with Docker:
```bash
docker build -t spot-nake .
docker run -p 7860:7860 --env-file .env -v spotnake-data:/data spot-nake
```

### Hugging Face Spaces Deployment
The Space configuration runs on a custom Docker image defined in `Dockerfile`. It exposes port `7860` for a lightweight `aiohttp` health server, allowing the Space to perform active health probes.

To deploy to Hugging Face Spaces:
1. Initialize a git repository:
   ```bash
   git init
   git remote add hf https://huggingface.co/spaces/username/space-name
   ```
2. Commit and push:
   ```bash
   git add .
   git commit -m "Deploy SpotNake"
   git push hf main --force
   ```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
