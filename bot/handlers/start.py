"""
Start Handler — /start and /help commands.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.utils.formatting import welcome_message

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    if not _is_owner(update, context):
        return
    
    await update.message.reply_text(
        welcome_message(),
        parse_mode=ParseMode.HTML,
    )
    logger.info("Sent welcome message")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    if not _is_owner(update, context):
        return
    
    await update.message.reply_text(
        welcome_message(),
        parse_mode=ParseMode.HTML,
    )


def _is_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the message is from the bot owner."""
    owner_id = context.bot_data.get("owner_id")
    if owner_id and update.effective_user.id != owner_id:
        logger.warning(f"Unauthorized user: {update.effective_user.id}")
        return False
    return True
