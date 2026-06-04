"""
Formatting — Telegram message helpers.

Provides safe markdown formatting and message construction
for sending rich responses via the Telegram Bot API.
"""

from __future__ import annotations

from html import escape


def bold(text: str) -> str:
    """HTML bold for Telegram."""
    return f"<b>{escape(text)}</b>"


def italic(text: str) -> str:
    """HTML italic for Telegram."""
    return f"<i>{escape(text)}</i>"


def code(text: str) -> str:
    """HTML code for Telegram."""
    return f"<code>{escape(text)}</code>"


def track_caption(title: str, artist: str, mood: str = "") -> str:
    """Format a track caption for the audio message."""
    parts = [f"🎵 {bold(title)}", f"🎤 {italic(artist)}"]
    if mood:
        parts.append(f"💫 {italic(mood)}")
    parts.append("\n🐍 <i>curated by SpotNake</i>")
    return "\n".join(parts)


def status_message(
    providers: dict[str, str],
    db_ok: bool,
    tracks_count: int,
) -> str:
    """Format the /health status message."""
    lines = ["🐍 <b>SpotNake Status</b>\n"]
    
    # Provider statuses
    lines.append("<b>AI Providers:</b>")
    for name, status in providers.items():
        emoji = "🟢" if "ok" in status.lower() else "🔴"
        lines.append(f"  {emoji} {name}: {status}")
    
    # Database
    db_emoji = "🟢" if db_ok else "🔴"
    lines.append(f"\n<b>Database:</b> {db_emoji} {'Connected' if db_ok else 'Disconnected'}")
    
    # Stats
    lines.append(f"<b>Tracks in library:</b> {tracks_count}")
    
    return "\n".join(lines)


def welcome_message() -> str:
    """Format the /start welcome message."""
    return (
        "🐍 <b>Welcome to SpotNake!</b>\n\n"
        "I'm your AI music curator. Just tell me what you want to hear:\n\n"
        "💬 <i>\"something chill for a late night drive\"</i>\n"
        "🎵 <i>\"play Blinding Lights by The Weeknd\"</i>\n"
        "🎨 <i>\"dark electronic like Gesaffelstein\"</i>\n"
        "😊 <i>\"I'm feeling happy and energetic\"</i>\n\n"
        "<b>Commands:</b>\n"
        "/mood <i>descriptor</i> — get a track matching a mood\n"
        "/taste — see your taste profile\n"
        "/health — check system status\n"
        "/help — show this message\n\n"
        "Just type naturally — I'll figure out the rest. 🎶"
    )
