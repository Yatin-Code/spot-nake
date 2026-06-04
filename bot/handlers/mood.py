"""
Mood Handler — /mood command.

Allows the user to request music by mood descriptor directly.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.ai.intents import MusicIntent
from bot.handlers.music import _music_pipeline

logger = logging.getLogger(__name__)


async def mood_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mood <descriptor> — get a track matching a mood.
    
    Examples:
        /mood chill
        /mood dark electronic
        /mood happy energetic workout
    """
    if not update.message:
        return
    
    # Owner check
    owner_id = context.bot_data.get("owner_id")
    if owner_id and update.effective_user.id != owner_id:
        return
    
    # Extract mood from command args
    if not context.args:
        await update.message.reply_text(
            "🐍 Tell me a mood! Example: <code>/mood chill late night</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    
    mood_text = " ".join(context.args)
    
    # Construct a mood intent directly
    intent = MusicIntent(
        type="mood",
        query=mood_text,
        mood=mood_text,
    )
    
    logger.info(f"Mood command: {mood_text}")
    await _music_pipeline(update, context, intent, f"/mood {mood_text}")
