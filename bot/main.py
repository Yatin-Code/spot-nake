"""
SpotNake Main Entry Point

Initializes all services (Database, AI Router, Embeddings, Taste Store),
registers Telegram command and message handlers, starts the aiohttp health
server on port 7860 (for Hugging Face Spaces), and runs the Telegram bot.
"""

from __future__ import annotations

import socket

# Force IPv4 resolution to bypass Docker IPv6 routing blackholes
_old_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _old_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

import asyncio
import logging
import sys
from aiohttp import web
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from bot.config import Settings
from bot.storage.db import Database
from bot.ai.router import AIRouter
from bot.ai.embeddings import EmbeddingService
from bot.storage.taste import TasteProfileStore
from bot.handlers import (
    start_handler,
    help_handler,
    mood_handler,
    music_handler,
    taste_handler,
    health_handler,
    stats_handler,
)

logger = logging.getLogger(__name__)


async def handle_health(request: web.Request) -> web.Response:
    """HTTP Health Check endpoint."""
    return web.Response(text="🟢 SpotNake is running and healthy", content_type="text/plain")


async def start_health_server(port: int) -> web.AppRunner:
    """Start the HTTP health server on the specified port.
    
    Hugging Face Spaces expects a web server to bind to port 7860.
    """
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🟢 Health server listening on port {port}")
    return runner


async def main() -> None:
    """Main function to initialize and start the SpotNake bot."""
    # 1. Load Settings
    settings = Settings()
    
    # 2. Configure Logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger.info("Starting SpotNake V1...")

    # 3. Initialize Database
    db = Database()
    await db.connect(settings.mongodb_uri, settings.db_name)

    # 4. Initialize AI Services
    router = AIRouter(settings)
    embeddings = EmbeddingService(
        api_key=settings.gemini_api_key,
        model=settings.embedding_model,
    )
    taste = TasteProfileStore(db)

    # 5. Initialize Telegram Application with extended network timeouts and custom base URL
    builder = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
    )
    if settings.telegram_api_url:
        builder.base_url(settings.telegram_api_url)
        if "/bot" in settings.telegram_api_url:
            file_url = settings.telegram_api_url.replace("/bot", "/file/bot")
            builder.base_file_url(file_url)
            logger.info(f"Using custom base_file_url: {file_url}")
        logger.info(f"Using custom base_url: {settings.telegram_api_url}")
    app = builder.build()

    # Store references in bot_data for handlers to access
    app.bot_data["db"] = db
    app.bot_data["router"] = router
    app.bot_data["embeddings"] = embeddings
    app.bot_data["taste"] = taste
    app.bot_data["settings"] = settings
    app.bot_data["owner_id"] = settings.telegram_owner_id

    # 6. Register Telegram Handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("mood", mood_handler))
    app.add_handler(CommandHandler("taste", taste_handler))
    app.add_handler(CommandHandler("health", health_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, music_handler))

    # 7. Start Health Web Server
    runner = await start_health_server(settings.port)

    # 8. Start Telegram Bot Polling
    logger.info("Bot handlers registered. Starting polling loop...")
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    
    def handle_signal():
        logger.info("Signal received. Initiating shutdown...")
        stop_event.set()
        
    import signal
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass

    try:
        async with app:
            await app.initialize()
            await app.start()
            
            # Send startup notification to owner
            try:
                await app.bot.send_message(chat_id=settings.telegram_owner_id, text="hello")
                logger.info(f"Sent startup message 'hello' to owner {settings.telegram_owner_id}")
            except Exception as e:
                logger.error(f"Failed to send startup message: {e}")

            await app.updater.start_polling()
            await stop_event.wait()
            
            logger.info("Stopping polling...")
            await app.updater.stop()
            await app.stop()
    except Exception as e:
        logger.critical(f"Bot crashed: {e}", exc_info=True)
    finally:
        logger.info("Shutting down SpotNake...")
        await runner.cleanup()
        await db.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("SpotNake stopped by user.")
    except Exception as e:
        logger.critical(f"SpotNake crashed with unhandled exception: {e}", exc_info=True)
        sys.exit(1)
