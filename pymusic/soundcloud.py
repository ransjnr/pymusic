"""SoundCloud downloader for pyMusic."""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

from pymusic.config import Config
from pymusic.downloader import build_ydl_opts, extract_info, download_track as _download_track
from pymusic.exceptions import DownloadError, PlaylistError, SearchError
from pymusic.models import Playlist, SearchResult, Source, Track, DownloadStatus
from pymusic.utils import is_soundcloud_set, sanitize_filename

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Info helpers
# ---------------------------------------------------------------------------

def _info_to_track(info: dict, track_number: int = 0, total: int = 0) -> Track:
    title = info.get("title") or ""
    artist = info.get("uploader") or info.get("artist") or ""
    album = info.get("album") or ""
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
        source=Source.SOUNDCLOUD,
        track_number=track_number,
        total_tracks=total,
        genre=info.get("genre") or "",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_track_info(url: str, config: Config) -> Track:
    """Fetch metadata for a SoundCloud track without downloading."""
    opts = build_ydl_opts(config, "/tmp/%(id)s.%(ext)s")
    info = extract_info(url, opts)
    return _info_to_track(info)


def get_set_info(url: str, config: Config) -> Playlist:
    """Fetch metadata for a SoundCloud set (playlist) without downloading."""
    opts = build_ydl_opts(config, "/tmp/%(id)s.%(ext)s")
    opts["extract_flat"] = True
    info = extract_info(url, opts)

    if not info:
        raise PlaylistError(f"Could not fetch SoundCloud set info for {url}")

    entries = info.get("entries") or []
    total = len(entries)
    tracks = []
    for i, entry in enumerate(entries, start=1):
        if not entry:
            continue
        track = Track(
            url=entry.get("url") or entry.get("webpage_url") or "",
            title=entry.get("title") or "",
            artist=entry.get("uploader") or "",
            duration=float(entry.get("duration") or 0),
            thumbnail_url=entry.get("thumbnail") or "",
            source=Source.SOUNDCLOUD,
            track_number=i,
            total_tracks=total,
        )
        tracks.append(track)

    return Playlist(
        url=url,
        title=info.get("title") or "",
        description=info.get("description") or "",
        uploader=info.get("uploader") or "",
        thumbnail_url=info.get("thumbnail") or "",
        source=Source.SOUNDCLOUD,
        tracks=tracks,
    )


def download_track(
    url: str,
    config: Config,
    progress_callback: Optional[Callable] = None,
) -> Track:
    """Download a single SoundCloud track."""
    try:
        track = get_track_info(url, config)
    except DownloadError:
        track = Track(url=url, source=Source.SOUNDCLOUD)

    _download_track(track, config, progress_callback)
    return track


def download_set(
    url: str,
    config: Config,
    progress_callback: Optional[Callable] = None,
    item_callback: Optional[Callable] = None,
) -> Playlist:
    """Download all tracks in a SoundCloud set/playlist."""
    playlist = get_set_info(url, config)
    tracks = playlist.tracks

    start = max(0, config.playlist_start - 1)
    end = config.playlist_end if config.playlist_end is not None else len(tracks)
    tracks = tracks[start:end]

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


def search_soundcloud(
    query: str,
    config: Config,
    limit: int = 10,
) -> List[SearchResult]:
    """Search SoundCloud and return a list of SearchResult objects."""
    search_url = f"scsearch{limit}:{query}"
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
        results.append(SearchResult(
            url=entry.get("url") or entry.get("webpage_url") or "",
            title=entry.get("title") or "",
            artist=entry.get("uploader") or "",
            duration=float(entry.get("duration") or 0),
            thumbnail_url=entry.get("thumbnail") or "",
            source=Source.SOUNDCLOUD,
        ))
    return results
