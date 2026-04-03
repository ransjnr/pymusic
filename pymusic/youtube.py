"""YouTube downloader for pyMusic."""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

import yt_dlp

from pymusic.config import Config
from pymusic.downloader import build_ydl_opts, extract_info, download_track as _download_track
from pymusic.exceptions import DownloadError, PlaylistError, SearchError
from pymusic.models import (
    Playlist, SearchResult, Source, Track, DownloadStatus
)
from pymusic.utils import (
    is_youtube_playlist, is_youtube_video, sanitize_filename, ensure_dir
)

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_PREFIX = "ytsearch"


# ---------------------------------------------------------------------------
# Info extraction helpers
# ---------------------------------------------------------------------------

def _info_to_track(info: dict, playlist_index: int = 0, total: int = 0) -> Track:
    """Convert a yt-dlp info dict to a Track."""
    title = info.get("title") or info.get("alt_title") or ""
    artist = (
        info.get("artist")
        or info.get("uploader")
        or info.get("channel")
        or ""
    )
    # YouTube Music often stores artist/album in extra fields
    album = info.get("album") or info.get("playlist_title") or ""
    year = str(info.get("release_year") or info.get("upload_date", "")[:4] or "")
    thumbnail = (
        info.get("thumbnail")
        or (info.get("thumbnails") or [{}])[-1].get("url", "")
    )
    return Track(
        url=info.get("webpage_url") or info.get("url") or "",
        title=title,
        artist=artist,
        album=album,
        year=year,
        duration=float(info.get("duration") or 0),
        thumbnail_url=thumbnail,
        source=Source.YOUTUBE,
        track_number=playlist_index,
        total_tracks=total,
        extra={"id": info.get("id"), "view_count": info.get("view_count")},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_track_info(url: str, config: Config) -> Track:
    """Fetch metadata for a single YouTube video without downloading."""
    opts = build_ydl_opts(config, "/tmp/%(id)s.%(ext)s")
    info = extract_info(url, opts)
    return _info_to_track(info)


def get_playlist_info(url: str, config: Config) -> Playlist:
    """Fetch metadata for all tracks in a YouTube playlist without downloading."""
    opts = build_ydl_opts(config, "/tmp/%(id)s.%(ext)s")
    opts["extract_flat"] = True
    info = extract_info(url, opts)

    if not info:
        raise PlaylistError(f"Could not fetch playlist info for {url}")

    entries = info.get("entries") or []
    total = len(entries)
    tracks = []
    for i, entry in enumerate(entries, start=1):
        if not entry:
            continue
        track_url = entry.get("url") or entry.get("webpage_url") or ""
        if not track_url.startswith("http"):
            track_url = f"https://www.youtube.com/watch?v={entry.get('id', '')}"
        track = Track(
            url=track_url,
            title=entry.get("title") or "",
            artist=entry.get("uploader") or entry.get("channel") or "",
            duration=float(entry.get("duration") or 0),
            thumbnail_url=entry.get("thumbnail") or "",
            source=Source.YOUTUBE,
            track_number=i,
            total_tracks=total,
        )
        tracks.append(track)

    playlist_thumb = (
        info.get("thumbnail")
        or (info.get("thumbnails") or [{}])[-1].get("url", "")
    )
    return Playlist(
        url=url,
        title=info.get("title") or "",
        description=info.get("description") or "",
        uploader=info.get("uploader") or "",
        thumbnail_url=playlist_thumb,
        source=Source.YOUTUBE,
        tracks=tracks,
    )


def download_single(
    url: str,
    config: Config,
    progress_callback: Optional[Callable] = None,
) -> Track:
    """Download a single YouTube video."""
    # Fetch metadata first
    try:
        track = get_track_info(url, config)
    except DownloadError:
        # Fallback: create a minimal track object
        track = Track(url=url, source=Source.YOUTUBE)

    _download_track(track, config, progress_callback)
    return track


def download_playlist(
    url: str,
    config: Config,
    progress_callback: Optional[Callable] = None,
    item_callback: Optional[Callable] = None,
) -> Playlist:
    """Download all tracks in a YouTube playlist.

    Args:
        url: Playlist URL.
        config: pyMusic configuration.
        progress_callback: Called with (track, downloaded_bytes, total_bytes, speed).
        item_callback: Called with (track, index, total) after each track completes.
    """
    playlist = get_playlist_info(url, config)
    tracks = playlist.tracks

    # Slice based on config
    start = max(0, config.playlist_start - 1)
    end = config.playlist_end if config.playlist_end is not None else len(tracks)
    tracks = tracks[start:end]

    if config.playlist_reverse:
        tracks = list(reversed(tracks))

    if config.playlist_random:
        import random
        tracks = random.sample(tracks, len(tracks))

    total = len(tracks)
    for i, track in enumerate(tracks, start=1):
        logger.info("Downloading %d/%d: %s", i, total, track.display_name)
        try:
            _download_track(track, config, progress_callback)
        except DownloadError as exc:
            logger.error("Failed to download %s: %s", track.display_name, exc)
            track.status = DownloadStatus.FAILED
            track.error = str(exc)

        if item_callback:
            item_callback(track, i, total)

    return playlist


def search_youtube(
    query: str,
    config: Config,
    limit: int = 10,
) -> List[SearchResult]:
    """Search YouTube and return a list of SearchResult objects."""
    search_url = f"{YOUTUBE_SEARCH_PREFIX}{limit}:{query}"
    opts = build_ydl_opts(config, "/tmp/%(id)s.%(ext)s")
    opts["extract_flat"] = True
    opts["quiet"] = True

    try:
        info = extract_info(search_url, opts)
    except DownloadError as exc:
        raise SearchError(query, str(exc)) from exc

    entries = info.get("entries") or []
    results = []
    for entry in entries:
        if not entry:
            continue
        url = entry.get("url") or ""
        if not url.startswith("http"):
            url = f"https://www.youtube.com/watch?v={entry.get('id', '')}"
        results.append(SearchResult(
            url=url,
            title=entry.get("title") or "",
            artist=entry.get("uploader") or entry.get("channel") or "",
            duration=float(entry.get("duration") or 0),
            thumbnail_url=entry.get("thumbnail") or "",
            source=Source.YOUTUBE,
            view_count=entry.get("view_count") or 0,
        ))
    return results


def search_and_download(
    query: str,
    config: Config,
    progress_callback: Optional[Callable] = None,
) -> Track:
    """Search YouTube for a query and download the first result."""
    results = search_youtube(query, config, limit=1)
    if not results:
        raise SearchError(query, "No results found")

    best = results[0]
    track = best.to_track()
    _download_track(track, config, progress_callback)
    return track
