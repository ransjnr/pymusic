"""Utility helpers for pyMusic."""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

_YOUTUBE_DOMAINS = {"youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
_SOUNDCLOUD_DOMAINS = {"soundcloud.com", "www.soundcloud.com", "on.soundcloud.com"}
_SPOTIFY_DOMAINS = {"open.spotify.com", "spotify.com"}
_BANDCAMP_RE = re.compile(r"https?://[\w-]+\.bandcamp\.com", re.IGNORECASE)


def detect_source(url: str) -> str:
    """Detect the music source from a URL.

    Returns one of: 'youtube', 'soundcloud', 'spotify', 'bandcamp', 'generic'.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if hostname in _YOUTUBE_DOMAINS:
        return "youtube"
    if hostname in _SOUNDCLOUD_DOMAINS:
        return "soundcloud"
    if hostname in _SPOTIFY_DOMAINS:
        return "spotify"
    if _BANDCAMP_RE.match(url):
        return "bandcamp"
    return "generic"


def is_youtube_playlist(url: str) -> bool:
    """Return True if the URL points to a YouTube playlist."""
    parsed = urlparse(url)
    if parsed.hostname not in _YOUTUBE_DOMAINS:
        return False
    qs = parse_qs(parsed.query)
    return "list" in qs and "v" not in qs


def is_youtube_video(url: str) -> bool:
    """Return True if the URL points to a single YouTube video."""
    parsed = urlparse(url)
    if parsed.hostname not in _YOUTUBE_DOMAINS:
        return False
    if parsed.hostname == "youtu.be":
        return True
    qs = parse_qs(parsed.query)
    return "v" in qs


def is_spotify_playlist(url: str) -> bool:
    """Return True if the Spotify URL is a playlist or album."""
    return "/playlist/" in url or "/album/" in url


def is_soundcloud_set(url: str) -> bool:
    """Return True if the SoundCloud URL is a set/playlist."""
    return "/sets/" in url


# ---------------------------------------------------------------------------
# File / path helpers
# ---------------------------------------------------------------------------

def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Return a filesystem-safe filename, removing or replacing illegal chars."""
    # Normalise unicode
    name = unicodedata.normalize("NFKC", name)
    # Replace illegal characters with underscores
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    # Collapse multiple spaces/underscores
    name = re.sub(r"_{2,}", "_", name)
    name = name.strip(". _")
    # Truncate
    if len(name) > max_length:
        name = name[:max_length].rstrip(". _")
    return name or "unknown"


def ensure_dir(path: Path) -> Path:
    """Create directory (and parents) if it does not exist; return path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_output_path(
    base_dir: Path,
    track_title: str,
    artist: str = "",
    album: str = "",
    fmt: str = "mp3",
    create_subdirs: bool = False,
) -> Path:
    """Build the full output file path for a track."""
    filename = sanitize_filename(track_title) + f".{fmt}"
    if create_subdirs:
        parts = []
        if artist:
            parts.append(sanitize_filename(artist))
        if album:
            parts.append(sanitize_filename(album))
        sub = base_dir.joinpath(*parts) if parts else base_dir
        ensure_dir(sub)
        return sub / filename
    ensure_dir(base_dir)
    return base_dir / filename


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_size(num_bytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    """Format seconds into MM:SS or H:MM:SS."""
    total = int(seconds)
    mins, secs = divmod(total, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


# ---------------------------------------------------------------------------
# Spotify helpers
# ---------------------------------------------------------------------------

def extract_spotify_id(url: str) -> Optional[str]:
    """Extract the Spotify entity ID from a URL."""
    match = re.search(r"spotify\.com/(?:track|album|playlist|artist)/([A-Za-z0-9]+)", url)
    return match.group(1) if match else None


def spotify_entity_type(url: str) -> Optional[str]:
    """Return 'track', 'album', 'playlist', or 'artist' for a Spotify URL."""
    for entity in ("track", "album", "playlist", "artist"):
        if f"/{entity}/" in url:
            return entity
    return None
