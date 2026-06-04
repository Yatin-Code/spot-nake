"""
Taste Handler — /taste command.

Displays a summary of the user's taste history, top artists, and moods.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.storage.taste import TasteProfileStore

logger = logging.getLogger(__name__)


async def taste_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /taste command to view the user's taste profile."""
    if not update.message:
        return
    
    # Owner check
    owner_id = context.bot_data.get("owner_id")
    if owner_id and update.effective_user.id != owner_id:
        logger.warning(f"Unauthorized taste request from user {update.effective_user.id}")
        return
    
    taste: TasteProfileStore = context.bot_data["taste"]
    
    try:
        summary = await taste.get_taste_summary()
        
        lines = [
            "🐍 <b>Your Taste Profile Summary</b>\n",
            f"📈 <b>Total unique tracks:</b> {summary['total_tracks']}",
            f"🎧 <b>Total plays:</b> {summary['total_plays']}\n",
            "🎤 <b>Top Artists:</b>"
        ]
        
        for artist in summary["top_artists"]:
            lines.append(f"  • {artist}")
            
        lines.append("\n💫 <b>Top Moods:</b>")
        for mood in summary["top_moods"]:
            lines.append(f"  • {mood}")
            
        lines.append("\n<i>Your taste profile updates automatically as you request and listen to music.</i>")
        
        await update.message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
        )
        logger.info("Sent taste profile summary")
    except Exception as e:
        logger.error(f"Error retrieving taste profile: {e}")
        await update.message.reply_text(
            "🐍 Couldn't retrieve your taste profile right now. Try playing some music first!",
            parse_mode=ParseMode.HTML,
        )
