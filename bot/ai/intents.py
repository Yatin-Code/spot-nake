"""
Intents — MusicIntent schema + system prompts.

Defines the structured output schema for intent parsing
and the system prompts used across all LLM providers.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class MusicIntent(BaseModel):
    """Structured intent extracted from a user's music-related message."""

    type: Literal["search", "mood", "similar", "chat"] = Field(
        description=(
            "search = direct song/artist request, "
            "mood = subjective/emotional description, "
            "similar = 'something like X' request, "
            "chat = non-music conversation"
        )
    )
    query: str = Field(
        default="",
        description="The main search query (song name, artist, or descriptive phrase)",
    )
    mood: Optional[str] = Field(
        default=None,
        description="Emotional descriptor: chill, energetic, melancholic, etc.",
    )
    genre: Optional[str] = Field(
        default=None,
        description="Music genre: pop, rock, electronic, hip-hop, etc.",
    )
    tempo: Optional[Literal["slow", "medium", "fast"]] = Field(
        default=None,
        description="Desired tempo/energy level",
    )
    context: Optional[str] = Field(
        default=None,
        description="Situational context: late night drive, workout, studying, etc.",
    )
    era: Optional[str] = Field(
        default=None,
        description="Time period preference: 90s, 2020s, classic, etc.",
    )
    language: Optional[str] = Field(
        default=None,
        description="Preferred language: english, hindi, spanish, etc.",
    )
    artist_hint: Optional[str] = Field(
        default=None,
        description="Artist similarity hint: 'like Radiohead', 'similar to Dua Lipa'",
    )

    @field_validator("query", mode="before")
    @classmethod
    def coerce_query(cls, v):
        if v is None:
            return ""
        return str(v)


# ── System Prompts ──

INTENT_SYSTEM_PROMPT = """You are SpotNake, an AI music intent parser. Given a user message, extract a JSON object with these fields:

- type: "search" (direct song/artist request), "mood" (subjective/emotional), "similar" (something like X), or "chat" (non-music)
- query: main search text (song name, artist, or descriptive phrase)
- mood: emotional descriptor (chill, energetic, melancholic, etc.) or null
- genre: music genre or null
- tempo: "slow", "medium", "fast", or null
- context: situational context (late night drive, workout, etc.) or null
- era: time period (90s, 2020s, etc.) or null
- language: preferred language or null
- artist_hint: artist similarity hint or null

Rules:
1. Always respond with VALID JSON ONLY. No markdown, no explanation, no code fences.
2. For "daylight is good" → type="search", query="Daylight"
3. For "something chill for studying" → type="mood", mood="chill", context="studying"
4. For "more like Shape of You" → type="similar", query="Shape of You", artist_hint="Ed Sheeran"
5. For "what kind of music do you like?" → type="chat"
6. Extract as many fields as you can infer from context.
"""

BANTER_SYSTEM_PROMPT = """You are SpotNake 🐍, a cool and knowledgeable music AI assistant on Telegram.

Personality:
- Passionate about music across all genres and eras
- Casual, friendly tone with occasional music puns
- Use emojis sparingly but naturally (🎵 🎶 🎸 🐍)
- Keep responses concise (2-4 sentences max)
- If the user seems to want music, gently steer them toward making a request
- You know about music history, production, artists, and genres

Never:
- Generate JSON or structured data in banter mode
- Pretend to play or stream music directly
- Give overly long responses
"""


def get_intent_schema() -> dict:
    """Return the JSON schema for MusicIntent (for Gemini structured output)."""
    return MusicIntent.model_json_schema()
