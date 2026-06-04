"""
Embeddings — Gemini gemini-embedding-001 wrapper.

Provides semantic vectorization for tracks and queries,
used by the taste profile system for similarity search.
"""

from __future__ import annotations

import logging
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Gemini gemini-embedding-001 for taste profile vectorization.
    
    Produces configurable dimensional vectors (configured to 768) 
    for semantic music similarity.
    """

    def __init__(self, api_key: str, model: str = "gemini-embedding-001", dimensions: int = 768):
        self.client = genai.Client(api_key=api_key)
        self.model = f"models/{model}"
        self.dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string into a vector.
        
        Args:
            text: The text to embed.
            
        Returns:
            Float vector of length self.dimensions.
        """
        try:
            result = await self.client.aio.models.embed_content(
                model=self.model,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=self.dimensions
                )
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    async def embed_track(
        self,
        artist: str,
        title: str,
        mood: Optional[str] = None,
        genre: Optional[str] = None,
        context: Optional[str] = None,
    ) -> list[float]:
        """Create a semantic fingerprint for a track.
        
        Combines metadata into a rich text representation before embedding.
        
        Args:
            artist: Track artist name.
            title: Track title.
            mood: Optional mood descriptor.
            genre: Optional genre.
            context: Optional listening context.
            
        Returns:
            Float vector of length self.dimensions.
        """
        parts = [f"{artist} - {title}"]
        if mood:
            parts.append(f"mood: {mood}")
        if genre:
            parts.append(f"genre: {genre}")
        if context:
            parts.append(f"context: {context}")
        
        composite = " | ".join(parts)
        logger.debug(f"Embedding track: {composite}")
        return await self.embed(composite)

    async def embed_query(self, query: str, mood: Optional[str] = None) -> list[float]:
        """Embed a search/mood query for similarity matching.
        
        Args:
            query: User's search query or mood description.
            mood: Optional explicit mood tag.
            
        Returns:
            Float vector of length self.dimensions.
        """
        text = query
        if mood:
            text += f" | mood: {mood}"
        return await self.embed(text)
