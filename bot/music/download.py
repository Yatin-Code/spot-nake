"""
Music Download — yt-dlp download + ffmpeg conversion.

Downloads audio from YouTube URLs, converts to MP3 via ffmpeg,
and applies ID3 tags using mutagen.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, ID3NoHeaderError

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of a successful download."""
    filepath: str
    title: str
    artist: str
    duration: int  # seconds
    filesize: int  # bytes


async def download_audio(
    url: str,
    download_dir: str,
    audio_format: str = "mp3",
    audio_quality: str = "320",
    title: Optional[str] = None,
    artist: Optional[str] = None,
) -> Optional[DownloadResult]:
    """Download audio from a YouTube URL.
    
    Uses yt-dlp to download and ffmpeg to convert to the desired format.
    
    Args:
        url: YouTube video URL.
        download_dir: Directory to save the downloaded file.
        audio_format: Output format (mp3, opus, m4a).
        audio_quality: Audio quality (320, 256, 192, 128).
        title: Optional title for the filename.
        artist: Optional artist for the filename.
        
    Returns:
        DownloadResult on success, None on failure.
    """
    # Ensure download directory exists
    os.makedirs(download_dir, exist_ok=True)
    
    # Build safe filename
    if title and artist:
        safe_name = _safe_filename(f"{artist} - {title}")
    elif title:
        safe_name = _safe_filename(title)
    else:
        safe_name = "%(title)s"
    
    output_template = os.path.join(download_dir, f"{safe_name}.%(ext)s")
    
    cmd = [
        "yt-dlp",
        url,
        "--extract-audio",
        "--audio-format", audio_format,
        "--audio-quality", audio_quality,
        "--output", output_template,
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--max-filesize", "50M",  # Telegram limit
        "--socket-timeout", "30",
    ]
    
    logger.info(f"⬇️ Downloading: {url}")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=120  # 2-minute timeout
        )
    except asyncio.TimeoutError:
        logger.error("Download timed out after 120s")
        return None
    except FileNotFoundError:
        logger.error("yt-dlp not found")
        return None
    
    if process.returncode != 0:
        error_msg = stderr.decode()[:300]
        logger.error(f"Download failed (exit {process.returncode}): {error_msg}")
        return None
    
    # Find the downloaded file
    filepath = _find_downloaded_file(download_dir, safe_name, audio_format)
    if not filepath:
        logger.error(f"Downloaded file not found in {download_dir}")
        return None
    
    # Apply ID3 tags if MP3
    if audio_format == "mp3" and title:
        _tag_mp3(filepath, title=title, artist=artist or "Unknown")
    
    # Get file info
    file_size = os.path.getsize(filepath)
    duration = _get_duration(filepath)
    
    logger.info(f"✅ Downloaded: {filepath} ({file_size / 1024 / 1024:.1f}MB)")
    
    return DownloadResult(
        filepath=filepath,
        title=title or safe_name,
        artist=artist or "Unknown",
        duration=duration,
        filesize=file_size,
    )


def cleanup_file(filepath: str) -> None:
    """Delete a downloaded file to save disk space."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.debug(f"🗑️ Cleaned up: {filepath}")
    except OSError as e:
        logger.warning(f"Failed to cleanup {filepath}: {e}")


def _safe_filename(name: str) -> str:
    """Convert a string to a safe filename."""
    # Remove or replace unsafe characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    # Limit length
    return name[:100] if name else "track"


def _find_downloaded_file(
    directory: str, base_name: str, ext: str
) -> Optional[str]:
    """Find the downloaded file in the directory.
    
    yt-dlp may modify the filename slightly, so we search for it.
    """
    # First try the exact filename
    exact = os.path.join(directory, f"{base_name}.{ext}")
    if os.path.exists(exact):
        return exact
    
    # Search for any recently created file with the right extension
    dir_path = Path(directory)
    candidates = sorted(
        dir_path.glob(f"*.{ext}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    
    if candidates:
        return str(candidates[0])
    
    return None


def _tag_mp3(filepath: str, title: str, artist: str, album: str = "SpotNake") -> None:
    """Apply ID3 tags to an MP3 file."""
    try:
        try:
            audio = MP3(filepath, ID3=ID3)
        except ID3NoHeaderError:
            audio = MP3(filepath)
            audio.add_tags()
        
        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text=artist))
        audio.tags.add(TALB(encoding=3, text=album))
        audio.save()
        logger.debug(f"Tagged: {title} by {artist}")
    except Exception as e:
        logger.warning(f"Failed to tag MP3: {e}")


def _get_duration(filepath: str) -> int:
    """Get the duration of an audio file in seconds."""
    try:
        audio = MP3(filepath)
        return int(audio.info.length)
    except Exception:
        return 0
