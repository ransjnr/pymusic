"""Spotify resolver for pyMusic.

Spotify does not allow direct audio download via its API.
This module resolves Spotify metadata (track title, artist, album, artwork)
and then delegates the actual download to YouTube search.
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

from pymusic.config import Config
from pymusic.exceptions import SpotifyAuthError, DownloadError, SearchError
from pymusic.models import Playlist, Source, Track, DownloadStatus
from pymusic.utils import extract_spotify_id, spotify_entity_type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Spotify client helpers
# ---------------------------------------------------------------------------

def _get_spotify_client(config: Config):
    """Return an authenticated spotipy.Spotify client."""
    if not config.has_spotify_credentials:
        raise SpotifyAuthError()

    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials
    except ImportError as exc:
        raise SpotifyAuthError(
            "spotipy is required for Spotify support. Install it with: pip install spotipy"
        ) from exc

    credentials = SpotifyClientCredentials(
        client_id=config.spotify_client_id,
        client_secret=config.spotify_client_secret,
    )
    return spotipy.Spotify(client_credentials_manager=credentials)


def _spotify_track_to_track(sp_track: dict, source: Source = Source.SPOTIFY) -> Track:
    """Convert a Spotify track dict to a pyMusic Track."""
    artists = sp_track.get("artists") or []
    artist_name = ", ".join(a["name"] for a in artists if a.get("name"))
    album_info = sp_track.get("album") or {}
    album_name = album_info.get("name") or ""
    album_artist_list = album_info.get("artists") or []
    album_artist = ", ".join(a["name"] for a in album_artist_list if a.get("name"))

    # Thumbnail: pick largest available
    images = album_info.get("images") or []
    thumbnail = images[0].get("url") if images else ""

    # Release year
    release_date = album_info.get("release_date") or ""
    year = release_date[:4] if release_date else ""

    return Track(
        url=sp_track.get("external_urls", {}).get("spotify") or "",
        title=sp_track.get("name") or "",
        artist=artist_name,
        album=album_name,
        album_artist=album_artist,
        year=year,
        duration=float((sp_track.get("duration_ms") or 0) / 1000),
        thumbnail_url=thumbnail,
        source=source,
        track_number=sp_track.get("track_number") or 0,
        genre="",
        extra={"spotify_id": sp_track.get("id")},
    )


# ---------------------------------------------------------------------------
# Public info API
# ---------------------------------------------------------------------------

def get_track_info(url: str, config: Config) -> Track:
    """Resolve Spotify track metadata."""
    sp = _get_spotify_client(config)
    track_id = extract_spotify_id(url)
    if not track_id:
        raise DownloadError(f"Could not extract Spotify track ID from URL: {url}", url=url)
    sp_track = sp.track(track_id)
    return _spotify_track_to_track(sp_track)


def get_album_info(url: str, config: Config) -> Playlist:
    """Resolve a Spotify album as a Playlist."""
    sp = _get_spotify_client(config)
    album_id = extract_spotify_id(url)
    sp_album = sp.album(album_id)

    tracks_data = sp_album.get("tracks", {}).get("items") or []
    total = len(tracks_data)

    # Album images
    images = sp_album.get("images") or []
    thumbnail = images[0].get("url") if images else ""
    release_date = sp_album.get("release_date") or ""
    year = release_date[:4]

    tracks = []
    for i, item in enumerate(tracks_data, start=1):
        # Inject album info into the item for consistent conversion
        item = dict(item)
        item.setdefault("album", sp_album)
        track = _spotify_track_to_track(item)
        track.track_number = i
        track.total_tracks = total
        tracks.append(track)

    return Playlist(
        url=url,
        title=sp_album.get("name") or "",
        description=sp_album.get("label") or "",
        uploader=", ".join(a["name"] for a in (sp_album.get("artists") or [])),
        thumbnail_url=thumbnail,
        source=Source.SPOTIFY,
        tracks=tracks,
    )


def get_playlist_info(url: str, config: Config) -> Playlist:
    """Resolve a Spotify playlist as a Playlist."""
    sp = _get_spotify_client(config)
    playlist_id = extract_spotify_id(url)
    sp_playlist = sp.playlist(playlist_id)

    items = sp_playlist.get("tracks", {}).get("items") or []
    # Handle pagination
    results = sp_playlist.get("tracks", {})
    while results.get("next"):
        results = sp.next(results)
        items.extend(results.get("items") or [])

    total = len(items)
    tracks = []
    for i, item in enumerate(items, start=1):
        sp_track = item.get("track")
        if not sp_track:
            continue
        track = _spotify_track_to_track(sp_track)
        track.track_number = i
        track.total_tracks = total
        tracks.append(track)

    images = sp_playlist.get("images") or []
    thumbnail = images[0].get("url") if images else ""

    return Playlist(
        url=url,
        title=sp_playlist.get("name") or "",
        description=sp_playlist.get("description") or "",
        uploader=sp_playlist.get("owner", {}).get("display_name") or "",
        thumbnail_url=thumbnail,
        source=Source.SPOTIFY,
        tracks=tracks,
    )


# ---------------------------------------------------------------------------
# Download (resolve then search YouTube)
# ---------------------------------------------------------------------------

def download_track(
    url: str,
    config: Config,
    progress_callback: Optional[Callable] = None,
) -> Track:
    """Resolve Spotify metadata then download via YouTube."""
    from pymusic.youtube import search_and_download, search_youtube
    from pymusic.downloader import download_track as _dl_track

    track = get_track_info(url, config)
    query = f"{track.artist} {track.title}" if track.artist else track.title

    logger.info("Searching YouTube for Spotify track: %s", query)
    results = search_youtube(query, config, limit=3)
    if not results:
        raise SearchError(query, f"No YouTube results found for Spotify track: {track.title}")

    # Pick the best match (first result, duration-matched if possible)
    best = _pick_best_match(results, track)
    track.url = best.url
    track.source = Source.SPOTIFY  # Keep source as Spotify for tagging

    _dl_track(track, config, progress_callback)
    return track


def download_playlist(
    url: str,
    config: Config,
    progress_callback: Optional[Callable] = None,
    item_callback: Optional[Callable] = None,
) -> Playlist:
    """Resolve a Spotify album/playlist and download via YouTube."""
    from pymusic.downloader import download_track as _dl_track
    from pymusic.youtube import search_youtube

    entity_type = spotify_entity_type(url)
    if entity_type == "album":
        playlist = get_album_info(url, config)
    else:
        playlist = get_playlist_info(url, config)

    tracks = playlist.tracks
    start = max(0, config.playlist_start - 1)
    end = config.playlist_end if config.playlist_end is not None else len(tracks)
    tracks = tracks[start:end]

    total = len(tracks)
    for i, track in enumerate(tracks, start=1):
        logger.info("Downloading %d/%d: %s", i, total, track.display_name)
        try:
            query = f"{track.artist} {track.title}" if track.artist else track.title
            results = search_youtube(query, config, limit=3)
            if not results:
                raise SearchError(query, "No YouTube results")
            best = _pick_best_match(results, track)
            track.url = best.url
            _dl_track(track, config, progress_callback)
        except (DownloadError, SearchError) as exc:
            logger.error("Failed to download %s: %s", track.display_name, exc)
            track.status = DownloadStatus.FAILED
            track.error = str(exc)

        if item_callback:
            item_callback(track, i, total)

    return playlist


def _pick_best_match(results, track: Track):
    """Pick the YouTube search result that best matches a Spotify track."""
    if not results:
        raise SearchError(track.title, "No results to match")

    if track.duration <= 0:
        return results[0]

    # Prefer result with closest duration
    def duration_diff(r):
        return abs(r.duration - track.duration)

    return min(results, key=duration_diff)
