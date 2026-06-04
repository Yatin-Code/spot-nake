"""
Music Search — yt-dlp search via subprocess.

Searches YouTube for music tracks and returns metadata
without downloading. Uses subprocess to avoid yt-dlp's
internal state management issues in async contexts.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result from YouTube."""
    title: str
    artist: str  # uploader/channel name
    url: str
    duration: int  # seconds
    view_count: int
    thumbnail: Optional[str] = None
    video_id: Optional[str] = None


async def search_youtube(
    query: str,
    max_results: int = 5,
) -> list[SearchResult]:
    """Search YouTube for music tracks.
    
    Uses yt-dlp's search functionality via subprocess
    for isolation and async compatibility.
    
    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        
    Returns:
        List of SearchResult objects.
    """
    cmd = [
        "yt-dlp",
        f"ytsearch{max_results}:{query}",
        "--dump-json",
        "--no-download",
        "--no-playlist",
        "--flat-playlist",
        "--quiet",
        "--no-warnings",
    ]
    
    logger.info(f"🔍 Searching YouTube: {query}")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=30
        )
    except asyncio.TimeoutError:
        logger.error("yt-dlp search timed out")
        return []
    except FileNotFoundError:
        logger.error("yt-dlp not found. Install with: pip install yt-dlp")
        return []
    
    if process.returncode != 0:
        logger.warning(f"yt-dlp search warning: {stderr.decode()[:200]}")
    
    results = []
    for line in stdout.decode().strip().split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            results.append(SearchResult(
                title=data.get("title", "Unknown"),
                artist=data.get("uploader", data.get("channel", "Unknown")),
                url=data.get("webpage_url", data.get("url", "")),
                duration=data.get("duration", 0) or 0,
                view_count=data.get("view_count", 0) or 0,
                thumbnail=data.get("thumbnail"),
                video_id=data.get("id"),
            ))
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse yt-dlp output line: {line[:100]}")
    
    logger.info(f"Found {len(results)} results for: {query}")
    return results


async def search_music(
    query: str,
    mood: Optional[str] = None,
    genre: Optional[str] = None,
    artist_hint: Optional[str] = None,
) -> list[SearchResult]:
    """Search for music with enhanced query construction.
    
    Builds a richer search query by combining the base query
    with mood, genre, and artist hints.
    
    Args:
        query: Base search query.
        mood: Optional mood descriptor to append.
        genre: Optional genre to append.
        artist_hint: Optional artist name to append.
        
    Returns:
        List of SearchResult objects.
    """
    # Build enhanced query
    parts = [query]
    if artist_hint and artist_hint.lower() not in query.lower():
        parts.append(artist_hint)
    if genre:
        parts.append(genre)
    if mood:
        parts.append(f"{mood} music")
    
    enhanced = " ".join(parts)
    
    # Search with the enhanced query
    results = await search_youtube(enhanced, max_results=5)
    
    # Filter out very long videos (likely not songs)
    results = [r for r in results if r.duration < 600]  # < 10 minutes
    
    if not results and parts != [query]:
        # Fallback to base query if enhanced returned nothing
        logger.info(f"Enhanced query returned nothing, trying base: {query}")
        results = await search_youtube(query, max_results=5)
        results = [r for r in results if r.duration < 600]
    
    return results
