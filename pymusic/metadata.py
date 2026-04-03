"""Audio metadata embedding using mutagen."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from pymusic.models import Track
from pymusic.exceptions import MetadataError

logger = logging.getLogger(__name__)


def embed_metadata(track: Track, file_path: str) -> bool:
    """Embed ID3/metadata tags into an audio file. Returns True on success."""
    path = Path(file_path)
    if not path.exists():
        logger.warning("File not found for metadata embedding: %s", file_path)
        return False

    ext = path.suffix.lower().lstrip(".")

    try:
        if ext == "mp3":
            return _embed_mp3(track, path)
        elif ext == "flac":
            return _embed_flac(track, path)
        elif ext in ("m4a", "aac", "mp4"):
            return _embed_m4a(track, path)
        elif ext == "ogg":
            return _embed_ogg(track, path)
        else:
            logger.debug("No metadata handler for extension: %s", ext)
            return False
    except Exception as exc:
        logger.warning("Failed to embed metadata in %s: %s", file_path, exc)
        return False


def _embed_mp3(track: Track, path: Path) -> bool:
    from mutagen.id3 import (
        ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TPE2,
        TRCK, TDRC, TCON, APIC
    )

    try:
        tags = ID3(str(path))
    except ID3NoHeaderError:
        tags = ID3()

    if track.title:
        tags["TIT2"] = TIT2(encoding=3, text=track.title)
    if track.artist:
        tags["TPE1"] = TPE1(encoding=3, text=track.artist)
    if track.album:
        tags["TALB"] = TALB(encoding=3, text=track.album)
    if track.album_artist:
        tags["TPE2"] = TPE2(encoding=3, text=track.album_artist)
    if track.track_number:
        trck = str(track.track_number)
        if track.total_tracks:
            trck = f"{trck}/{track.total_tracks}"
        tags["TRCK"] = TRCK(encoding=3, text=trck)
    if track.year:
        tags["TDRC"] = TDRC(encoding=3, text=str(track.year))
    if track.genre:
        tags["TCON"] = TCON(encoding=3, text=track.genre)

    tags.save(str(path), v2_version=3)
    return True


def _embed_flac(track: Track, path: Path) -> bool:
    from mutagen.flac import FLAC

    audio = FLAC(str(path))
    if track.title:
        audio["title"] = track.title
    if track.artist:
        audio["artist"] = track.artist
    if track.album:
        audio["album"] = track.album
    if track.album_artist:
        audio["albumartist"] = track.album_artist
    if track.track_number:
        audio["tracknumber"] = str(track.track_number)
    if track.total_tracks:
        audio["totaltracks"] = str(track.total_tracks)
    if track.year:
        audio["date"] = str(track.year)
    if track.genre:
        audio["genre"] = track.genre
    audio.save()
    return True


def _embed_m4a(track: Track, path: Path) -> bool:
    from mutagen.mp4 import MP4, MP4Cover
    import requests

    audio = MP4(str(path))
    if track.title:
        audio["\xa9nam"] = [track.title]
    if track.artist:
        audio["\xa9ART"] = [track.artist]
    if track.album:
        audio["\xa9alb"] = [track.album]
    if track.album_artist:
        audio["aART"] = [track.album_artist]
    if track.track_number:
        audio["trkn"] = [(track.track_number, track.total_tracks)]
    if track.year:
        audio["\xa9day"] = [str(track.year)]
    if track.genre:
        audio["\xa9gen"] = [track.genre]
    audio.save()
    return True


def _embed_ogg(track: Track, path: Path) -> bool:
    from mutagen.oggvorbis import OggVorbis

    audio = OggVorbis(str(path))
    if track.title:
        audio["title"] = [track.title]
    if track.artist:
        audio["artist"] = [track.artist]
    if track.album:
        audio["album"] = [track.album]
    if track.album_artist:
        audio["albumartist"] = [track.album_artist]
    if track.track_number:
        audio["tracknumber"] = [str(track.track_number)]
    if track.year:
        audio["date"] = [str(track.year)]
    if track.genre:
        audio["genre"] = [track.genre]
    audio.save()
    return True
