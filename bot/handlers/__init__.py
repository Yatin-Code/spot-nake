# SpotNake Handlers

from bot.handlers.start import start_handler, help_handler
from bot.handlers.mood import mood_handler
from bot.handlers.music import music_handler
from bot.handlers.taste import taste_handler
from bot.handlers.admin import health_handler, stats_handler

__all__ = [
    "start_handler",
    "help_handler",
    "mood_handler",
    "music_handler",
    "taste_handler",
    "health_handler",
    "stats_handler",
]
