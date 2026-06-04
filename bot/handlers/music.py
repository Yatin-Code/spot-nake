"""
Music Handler — The main music pipeline.

Handles natural language messages, runs them through the AI router
for intent parsing, searches/downloads music, and sends it back.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

from bot.ai.router import AIRouter, AllProvidersExhausted
from bot.ai.intents import MusicIntent
from bot.ai.embeddings import EmbeddingService
from bot.music.search import search_music
from bot.music.download import download_audio, cleanup_file
from bot.storage.taste import TasteProfileStore
from bot.utils.formatting import track_caption

logger = logging.getLogger(__name__)


async def music_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-text messages — the main music pipeline.
    
    Flow: Parse → Search → Download → Tag → Embed → Store → Send → Cleanup
    """
    if not update.message or not update.message.text:
        return
    
    # Owner check
    owner_id = context.bot_data.get("owner_id")
    if owner_id and update.effective_user.id != owner_id:
        return
    
    user_text = update.message.text.strip()
    if not user_text:
        return
    
    # Get services from bot_data
    router: AIRouter = context.bot_data["router"]
    embeddings: EmbeddingService = context.bot_data["embeddings"]
    taste: TasteProfileStore = context.bot_data["taste"]
    settings = context.bot_data["settings"]
    
    # ── Step 1: Parse Intent ──
    await update.message.chat.send_action(ChatAction.TYPING)
    
    try:
        intent = await router.parse_intent(user_text)
        logger.info(f"Intent: {intent.type} → query={intent.query}, mood={intent.mood}")
    except AllProvidersExhausted:
        await update.message.reply_text(
            "🐍 My brain is overloaded right now. All AI providers are rate-limited. "
            "Give me a minute and try again!",
            parse_mode=ParseMode.HTML,
        )
        return
    except Exception as e:
        logger.error(f"Intent parsing error: {e}")
        await update.message.reply_text(
            "🐍 Something went wrong parsing your request. Try again?",
            parse_mode=ParseMode.HTML,
        )
        return
    
    # ── Handle by intent type ──
    
    if intent.type == "chat":
        # Conversational banter — no music download
        response = await router.chat(user_text)
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)
        return
    
    # For music intents (search, mood, similar), run the pipeline
    await _music_pipeline(update, context, intent, user_text)


async def _music_pipeline(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    intent: MusicIntent,
    original_query: str,
) -> None:
    """Execute the full music delivery pipeline."""
    router: AIRouter = context.bot_data["router"]
    embeddings: EmbeddingService = context.bot_data["embeddings"]
    taste: TasteProfileStore = context.bot_data["taste"]
    settings = context.bot_data["settings"]
    
    # ── Step 2: Build search query ──
    search_query = intent.query
    
    if intent.type == "mood" and not search_query:
        # For pure mood requests, construct a descriptive query
        parts = []
        if intent.mood:
            parts.append(intent.mood)
        if intent.genre:
            parts.append(intent.genre)
        if intent.context:
            parts.append(intent.context)
        if intent.era:
            parts.append(intent.era)
        search_query = " ".join(parts) if parts else "popular music"
    
    if intent.type == "similar" and not search_query:
        search_query = original_query
    
    # ── Step 2b: Taste-augmented search (for mood/similar) ──
    if intent.type in ("mood", "similar"):
        try:
            query_emb = await embeddings.embed_query(
                search_query, mood=intent.mood
            )
            similar_tracks = await taste.find_similar(query_emb, limit=3)
            if similar_tracks:
                # Augment search with similar track names
                augment = ", ".join(
                    f"{t['artist']} {t['title']}" for t in similar_tracks[:2]
                )
                search_query = f"{search_query} {augment}"
                logger.info(f"Augmented query with taste: {search_query[:100]}")
        except Exception as e:
            logger.warning(f"Taste augmentation failed: {e}")
    
    # ── Step 3: Search YouTube ──
    await update.message.reply_text(
        f"🔍 <i>Searching for: {search_query[:80]}...</i>",
        parse_mode=ParseMode.HTML,
    )
    
    results = await search_music(
        query=search_query,
        mood=intent.mood,
        genre=intent.genre,
        artist_hint=intent.artist_hint,
    )
    
    if not results:
        await update.message.reply_text(
            "🐍 Couldn't find anything matching that. Try being more specific?",
            parse_mode=ParseMode.HTML,
        )
        return
    
    # Pick the best result (first one after filtering)
    best = results[0]
    
    # ── Step 4: Download ──
    await update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
    await update.message.reply_text(
        f"⬇️ <i>Downloading: {best.title}</i>",
        parse_mode=ParseMode.HTML,
    )
    
    dl_result = await download_audio(
        url=best.url,
        download_dir=settings.download_dir,
        audio_format=settings.audio_format,
        audio_quality=settings.audio_quality,
        title=best.title,
        artist=best.artist,
    )
    
    if not dl_result:
        await update.message.reply_text(
            "🐍 Download failed. The video might be restricted or too large. "
            "Try a different song?",
            parse_mode=ParseMode.HTML,
        )
        return
    
    # ── Step 5: Embed + Store ──
    try:
        track_embedding = await embeddings.embed_track(
            artist=dl_result.artist,
            title=dl_result.title,
            mood=intent.mood,
            genre=intent.genre,
            context=intent.context,
        )
        await taste.store_track(
            artist=dl_result.artist,
            title=dl_result.title,
            embedding=track_embedding,
            mood=intent.mood,
            genre=intent.genre,
            context=intent.context,
        )
        await taste.store_play(
            artist=dl_result.artist,
            title=dl_result.title,
            query=original_query,
            intent_type=intent.type,
            mood=intent.mood,
            source_url=best.url,
        )
        await taste.update_preferences(
            user_id=update.effective_user.id,
            artist=dl_result.artist,
            genre=intent.genre,
            mood=intent.mood,
        )
        logger.info(f"Stored taste data for: {dl_result.artist} - {dl_result.title}")
    except Exception as e:
        logger.warning(f"Taste storage failed (non-critical): {e}")
    
    # ── Step 6: Send audio ──
    caption = track_caption(
        title=dl_result.title,
        artist=dl_result.artist,
        mood=intent.mood or "",
    )
    
    try:
        await update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        with open(dl_result.filepath, "rb") as audio_file:
            await update.message.reply_audio(
                audio=audio_file,
                caption=caption,
                parse_mode=ParseMode.HTML,
                title=dl_result.title,
                performer=dl_result.artist,
                duration=dl_result.duration,
            )
        logger.info(f"🎵 Sent: {dl_result.artist} - {dl_result.title}")
    except Exception as e:
        logger.error(f"Failed to send audio: {e}")
        await update.message.reply_text(
            f"🐍 Found the song but couldn't send it (maybe too large for Telegram). "
            f"Here's the link: {best.url}",
            parse_mode=ParseMode.HTML,
        )
    
    # ── Cleanup ──
    cleanup_file(dl_result.filepath)
