"""
Models — MongoDB document schemas for taste vectors and play history.

These are Pydantic models representing the shape of documents
stored in MongoDB collections.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TasteVector(BaseModel):
    """A single taste vector document in MongoDB.
    
    Represents a track the user has listened to / requested,
    along with its semantic embedding for similarity search.
    """
    track_id: str = Field(description="Unique identifier (artist-title hash)")
    title: str
    artist: str
    embedding: list[float] = Field(description="768-dim Gemini embedding")
    mood: Optional[str] = None
    genre: Optional[str] = None
    context: Optional[str] = None
    play_count: int = 1
    first_played: datetime = Field(default_factory=datetime.utcnow)
    last_played: datetime = Field(default_factory=datetime.utcnow)


class PlayHistoryEntry(BaseModel):
    """A single play history entry.
    
    Records each time a track is requested/downloaded.
    """
    track_id: str
    title: str
    artist: str
    query: str = Field(description="Original user query that triggered this")
    intent_type: str = Field(description="search, mood, similar, or chat")
    mood: Optional[str] = None
    source_url: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UserPreferences(BaseModel):
    """Aggregated user preference metadata.
    
    Updated incrementally as the user interacts with the bot.
    """
    user_id: int
    favorite_genres: dict[str, int] = Field(
        default_factory=dict,
        description="Genre → play count mapping",
    )
    favorite_moods: dict[str, int] = Field(
        default_factory=dict,
        description="Mood → play count mapping",
    )
    favorite_artists: dict[str, int] = Field(
        default_factory=dict,
        description="Artist → play count mapping",
    )
    total_tracks: int = 0
    last_active: datetime = Field(default_factory=datetime.utcnow)
