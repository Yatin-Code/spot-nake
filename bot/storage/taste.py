"""
Taste Profile Store — MongoDB-backed taste vector storage with cosine similarity.

Stores track embeddings and performs brute-force cosine similarity
search in Python (via NumPy). For V1, this is sufficient for
datasets under 10,000 tracks. V2 can upgrade to MongoDB Atlas
Vector Search for server-side ANN queries.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Optional

import numpy as np

from bot.storage.db import Database
from bot.storage.models import TasteVector, PlayHistoryEntry

logger = logging.getLogger(__name__)


def _track_id(artist: str, title: str) -> str:
    """Generate a deterministic track ID from artist + title."""
    key = f"{artist.lower().strip()}-{title.lower().strip()}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_np = np.array(a, dtype=np.float32)
    b_np = np.array(b, dtype=np.float32)
    dot = np.dot(a_np, b_np)
    norm = np.linalg.norm(a_np) * np.linalg.norm(b_np)
    if norm == 0:
        return 0.0
    return float(dot / norm)


class TasteProfileStore:
    """MongoDB-backed taste vector storage with cosine similarity search."""

    def __init__(self, db: Database):
        self.db = db

    async def store_track(
        self,
        artist: str,
        title: str,
        embedding: list[float],
        mood: Optional[str] = None,
        genre: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """Store a track's embedding in the taste profile using an atomic upsert."""
        tid = _track_id(artist, title)
        
        result = await self.db.taste_vectors.update_one(
            {"track_id": tid},
            {
                "$inc": {"play_count": 1},
                "$set": {"last_played": datetime.utcnow()},
                "$setOnInsert": {
                    "title": title,
                    "artist": artist,
                    "embedding": embedding,
                    "mood": mood,
                    "genre": genre,
                    "context": context,
                    "first_played": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        if result.upserted_id:
            logger.info(f"Stored new taste vector: {artist} - {title}")
        else:
            logger.info(f"Updated taste vector: {artist} - {title}")
            
        return tid

    async def store_play(
        self,
        artist: str,
        title: str,
        query: str,
        intent_type: str,
        mood: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> None:
        """Record a play/download event in history."""
        entry = PlayHistoryEntry(
            track_id=_track_id(artist, title),
            title=title,
            artist=artist,
            query=query,
            intent_type=intent_type,
            mood=mood,
            source_url=source_url,
        ).model_dump()
        await self.db.play_history.insert_one(entry)

    async def update_preferences(
        self,
        user_id: int,
        artist: str,
        genre: Optional[str] = None,
        mood: Optional[str] = None,
    ) -> None:
        """Incrementally update user preference counters."""
        updates = {
            "$inc": {"total_tracks": 1},
            "$set": {"last_active": datetime.utcnow()},
        }
        
        # Increment artist count
        updates["$inc"][f"favorite_artists.{artist}"] = 1
        
        if genre:
            updates["$inc"][f"favorite_genres.{genre}"] = 1
        if mood:
            updates["$inc"][f"favorite_moods.{mood}"] = 1
        
        await self.db.user_preferences.update_one(
            {"user_id": user_id},
            updates,
            upsert=True,
        )

    async def find_similar(
        self,
        query_embedding: list[float],
        limit: int = 5,
        exclude_ids: Optional[list[str]] = None,
    ) -> list[dict]:
        """Find tracks most similar to the query embedding.
        
        Brute-force cosine similarity in Python (fast enough for <10K tracks).
        """
        exclude = set(exclude_ids or [])
        
        # PyMongo Async natively supports 'async for' on cursors
        cursor = self.db.taste_vectors.find(
            {}, {"track_id": 1, "title": 1, "artist": 1, "embedding": 1, "mood": 1, "genre": 1}
        )
        
        all_docs = []
        async for doc in cursor:
            all_docs.append(doc)
            
        if not all_docs:
            return []
        
        scored = []
        for doc in all_docs:
            if doc["track_id"] in exclude:
                continue
            score = _cosine_similarity(query_embedding, doc["embedding"])
            scored.append((score, doc))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        
        results = []
        for score, doc in scored[:limit]:
            doc["similarity_score"] = round(score, 4)
            doc.pop("embedding", None)  # Don't return the raw vector
            doc.pop("_id", None)
            results.append(doc)
        
        return results

    async def get_taste_summary(self) -> dict:
        """Get a summary of the user's taste profile."""
        total = await self.db.taste_vectors.count_documents({})
        plays = await self.db.play_history.count_documents({})
        
        # Get top artists
        pipeline = [
            {"$group": {"_id": "$artist", "count": {"$sum": "$play_count"}}},
            {"$sort": {"count": -1}},
            {"$limit": 5},
        ]
        top_artists = []
        async for doc in self.db.taste_vectors.aggregate(pipeline):
            top_artists.append(f"{doc['_id']} ({doc['count']})")
        
        # Get top moods
        mood_pipeline = [
            {"$match": {"mood": {"$ne": None}}},
            {"$group": {"_id": "$mood", "count": {"$sum": "$play_count"}}},
            {"$sort": {"count": -1}},
            {"$limit": 5},
        ]
        top_moods = []
        async for doc in self.db.taste_vectors.aggregate(mood_pipeline):
            top_moods.append(f"{doc['_id']} ({doc['count']})")
        
        return {
            "total_tracks": total,
            "total_plays": plays,
            "top_artists": top_artists or ["No data yet"],
            "top_moods": top_moods or ["No data yet"],
        }
