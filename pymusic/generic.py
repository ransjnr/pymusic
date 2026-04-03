"""Generic downloader for any yt-dlp supported URL (Bandcamp, Vimeo, etc.)."""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

from pymusic.config import Config
from pymusic.downloader import build_ydl_opts, extract_info, download_track as _download_track
from pymusic.exceptions import DownloadError, PlaylistError
from pymusic.models import Playlist, Source, Track, DownloadStatus

logger = logging.getLogger(__name__)


def _detect_source_from_info(info: dict) -> Source:
    extractor = (info.get("extractor") or "").lower()
    if "bandcamp" in extractor:
        return Source.BANDCAMP
    if "soundcloud" in extractor:
        return Source.SOUNDCLOUD
    if "youtube" in extractor:
        return Source.YOUTUBE
    return Source.GENERIC


def _info_to_track(info: dict, track_number: int = 0, total: int = 0) -> Track:
    source = _detect_source_from_info(info)
    thumbnail = (
        info.get("thumbnail")
        or (info.get("thumbnails") or [{}])[-1].get("url", "")
    )
    year = str(info.get("release_year") or info.get("upload_date", "")[:4] or "")
    return Track(
        url=info.get("webpage_url") or info.get("url") or "",
        title=info.get("title") or "",
        artist=info.get("artist") or info.get("uploader") or "",
        album=info.get("album") or "",
        year=year,
        duration=float(info.get("duration") or 0),
        thumbnail_url=thumbnail,
        source=source,
        track_number=track_number,
        total_tracks=total,
        genre=info.get("genre") or "",
    )


def get_info(url: str, config: Config) -> dict:
    """Return raw yt-dlp info dict for a URL."""
    opts = build_ydl_opts(config, "/tmp/%(id)s.%(ext)s")
    return extract_info(url, opts)


def download_url(
    url: str,
    config: Config,
    progress_callback: Optional[Callable] = None,
) -> Track:
    """Download any yt-dlp supported single URL."""
    try:
        info = get_info(url, config)
        track = _info_to_track(info)
    except DownloadError:
        track = Track(url=url, source=Source.GENERIC)

    _download_track(track, config, progress_callback)
    return track


def download_playlist_url(
    url: str,
    config: Config,
    progress_callback: Optional[Callable] = None,
    item_callback: Optional[Callable] = None,
) -> Playlist:
    """Download all items from a generic playlist URL."""
    opts = build_ydl_opts(config, "/tmp/%(id)s.%(ext)s")
    opts["extract_flat"] = True
    info = extract_info(url, opts)

    if not info:
        raise PlaylistError(f"Could not fetch playlist info for {url}")

    entries = info.get("entries") or []
    total = len(entries)
    source = _detect_source_from_info(info)

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
            source=source,
            track_number=i,
            total_tracks=total,
        )
        tracks.append(track)

    playlist = Playlist(
        url=url,
        title=info.get("title") or "",
        description=info.get("description") or "",
        uploader=info.get("uploader") or "",
        thumbnail_url=info.get("thumbnail") or "",
        source=source,
        tracks=tracks,
    )

    tracks_slice = tracks
    start = max(0, config.playlist_start - 1)
    end = config.playlist_end if config.playlist_end is not None else len(tracks_slice)
    tracks_slice = tracks_slice[start:end]

    for i, track in enumerate(tracks_slice, start=1):
        logger.info("Downloading %d/%d: %s", i, len(tracks_slice), track.display_name)
        try:
            _download_track(track, config, progress_callback)
        except DownloadError as exc:
            logger.error("Failed: %s – %s", track.display_name, exc)
            track.status = DownloadStatus.FAILED
            track.error = str(exc)

        if item_callback:
            item_callback(track, i, len(tracks_slice))

    return playlist
