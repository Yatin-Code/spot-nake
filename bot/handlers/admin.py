"""
Admin Handler — /health and /stats commands (owner-only).
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.utils.formatting import status_message

logger = logging.getLogger(__name__)


async def health_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /health command to check system status."""
    if not update.message:
        return
    
    # Owner check
    owner_id = context.bot_data.get("owner_id")
    if owner_id and update.effective_user.id != owner_id:
        logger.warning(f"Unauthorized health check request from user {update.effective_user.id}")
        return
    
    router = context.bot_data["router"]
    db = context.bot_data["db"]
    
    try:
        # Check providers status
        providers = router.get_provider_status()
        
        # Check db connection
        db_ok = await db.is_connected()
        
        # Get tracks count
        tracks_count = await db.taste_vectors.count_documents({})
        
        msg = status_message(providers, db_ok, tracks_count)
        
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        logger.info("Sent health status message")
    except Exception as e:
        logger.error(f"Error in health handler: {e}")
        await update.message.reply_text("🐍 Error checking system health.", parse_mode=ParseMode.HTML)


async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command to view system stats."""
    if not update.message:
        return
    
    # Owner check
    owner_id = context.bot_data.get("owner_id")
    if owner_id and update.effective_user.id != owner_id:
        return
    
    db = context.bot_data["db"]
    try:
        vector_count = await db.taste_vectors.count_documents({})
        history_count = await db.play_history.count_documents({})
        pref_count = await db.user_preferences.count_documents({})
        
        lines = [
            "📊 <b>SpotNake System Stats</b>\n",
            f"👤 <b>Registered preference profiles:</b> {pref_count}",
            f"🎵 <b>Unique tracks embedded:</b> {vector_count}",
            f"🎧 <b>Total playback history events:</b> {history_count}"
        ]
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
        logger.info("Sent system stats message")
    except Exception as e:
        logger.error(f"Error in stats handler: {e}")
        await update.message.reply_text("🐍 Error retrieving system statistics.", parse_mode=ParseMode.HTML)
