"""Data models for pyMusic."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class AudioFormat(str, Enum):
    MP3 = "mp3"
    M4A = "m4a"
    FLAC = "flac"
    WAV = "wav"
    OGG = "ogg"

    @classmethod
    def from_string(cls, value: str) -> "AudioFormat":
        try:
            return cls(value.lower())
        except ValueError:
            from pymusic.exceptions import FormatError
            raise FormatError(value)


class Source(str, Enum):
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    SPOTIFY = "spotify"
    BANDCAMP = "bandcamp"
    GENERIC = "generic"


class DownloadStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Track:
    """Represents a single music track."""

    url: str
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    track_number: int = 0
    total_tracks: int = 0
    year: str = ""
    genre: str = ""
    duration: float = 0.0          # seconds
    thumbnail_url: str = ""
    source: Source = Source.GENERIC
    status: DownloadStatus = DownloadStatus.PENDING
    file_path: str = ""
    error: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        if self.artist and self.title:
            return f"{self.artist} - {self.title}"
        return self.title or self.url

    @property
    def duration_str(self) -> str:
        if not self.duration:
            return "Unknown"
        mins, secs = divmod(int(self.duration), 60)
        hours, mins = divmod(mins, 60)
        if hours:
            return f"{hours}:{mins:02d}:{secs:02d}"
        return f"{mins}:{secs:02d}"

    @property
    def is_downloaded(self) -> bool:
        return self.status == DownloadStatus.COMPLETED and bool(self.file_path) and os.path.exists(self.file_path)

    def __repr__(self) -> str:
        return f"Track(title={self.title!r}, artist={self.artist!r}, source={self.source.value})"


@dataclass
class Playlist:
    """Represents a music playlist."""

    url: str
    title: str = ""
    description: str = ""
    uploader: str = ""
    thumbnail_url: str = ""
    source: Source = Source.GENERIC
    tracks: List[Track] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    @property
    def total_tracks(self) -> int:
        return len(self.tracks)

    @property
    def downloaded_tracks(self) -> List[Track]:
        return [t for t in self.tracks if t.is_downloaded]

    @property
    def failed_tracks(self) -> List[Track]:
        return [t for t in self.tracks if t.status == DownloadStatus.FAILED]

    @property
    def duration(self) -> float:
        return sum(t.duration for t in self.tracks)

    @property
    def duration_str(self) -> str:
        total = int(self.duration)
        mins, secs = divmod(total, 60)
        hours, mins = divmod(mins, 60)
        if hours:
            return f"{hours}h {mins}m {secs}s"
        return f"{mins}m {secs}s"

    def __repr__(self) -> str:
        return f"Playlist(title={self.title!r}, tracks={self.total_tracks}, source={self.source.value})"


@dataclass
class SearchResult:
    """A single result from a music search."""

    url: str
    title: str
    artist: str = ""
    duration: float = 0.0
    thumbnail_url: str = ""
    source: Source = Source.YOUTUBE
    view_count: int = 0
    extra: dict = field(default_factory=dict)

    def to_track(self) -> Track:
        return Track(
            url=self.url,
            title=self.title,
            artist=self.artist,
            duration=self.duration,
            thumbnail_url=self.thumbnail_url,
            source=self.source,
        )

    @property
    def display_name(self) -> str:
        if self.artist:
            return f"{self.artist} - {self.title}"
        return self.title

    @property
    def duration_str(self) -> str:
        if not self.duration:
            return ""
        mins, secs = divmod(int(self.duration), 60)
        return f"{mins}:{secs:02d}"

    def __repr__(self) -> str:
        return f"SearchResult(title={self.title!r}, artist={self.artist!r})"


@dataclass
class DownloadResult:
    """Result of a download operation."""

    track: Track
    success: bool
    file_path: str = ""
    error: str = ""

    def __bool__(self) -> bool:
        return self.success
