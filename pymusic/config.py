"""Configuration management for pyMusic."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pymusic.models import AudioFormat
from pymusic.exceptions import ConfigurationError

SUPPORTED_FORMATS = {fmt.value for fmt in AudioFormat}
SUPPORTED_QUALITIES = {64, 96, 128, 192, 256, 320}


@dataclass
class Config:
    """Central configuration object for pyMusic."""

    # Output settings
    output_dir: str = field(default_factory=lambda: str(Path.home() / "Music"))
    format: str = "mp3"
    quality: int = 192          # kbps (only for lossy formats)
    create_subdirs: bool = False  # Organise as Artist/Album/Track

    # Metadata
    embed_metadata: bool = True
    embed_thumbnail: bool = True
    overwrite: bool = False

    # Playlist
    playlist_start: int = 1     # 1-indexed start position
    playlist_end: Optional[int] = None  # None = download all
    playlist_reverse: bool = False
    playlist_random: bool = False

    # Network
    rate_limit: Optional[str] = None   # e.g. "500K", "1M"
    retries: int = 3
    socket_timeout: int = 30
    proxy: Optional[str] = None

    # Spotify credentials
    spotify_client_id: Optional[str] = field(default=None)
    spotify_client_secret: Optional[str] = field(default=None)
    spotify_redirect_uri: str = "http://localhost:8888/callback"

    # Cookies (for age-restricted / member-only content)
    cookies_file: Optional[str] = None

    # Verbose / quiet mode
    verbose: bool = False
    quiet: bool = False

    def __post_init__(self):
        self._validate()
        self._resolve_env()

    def _validate(self):
        if self.format not in SUPPORTED_FORMATS:
            raise ConfigurationError(
                f"Invalid format {self.format!r}. Choose from: {', '.join(sorted(SUPPORTED_FORMATS))}"
            )
        if self.quality not in SUPPORTED_QUALITIES and self.format == "mp3":
            raise ConfigurationError(
                f"Invalid quality {self.quality}. Choose from: {', '.join(str(q) for q in sorted(SUPPORTED_QUALITIES))}"
            )
        if self.playlist_start < 1:
            raise ConfigurationError("playlist_start must be >= 1")
        if self.playlist_end is not None and self.playlist_end < self.playlist_start:
            raise ConfigurationError("playlist_end must be >= playlist_start")

    def _resolve_env(self):
        """Fill in missing values from environment variables."""
        if not self.spotify_client_id:
            self.spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        if not self.spotify_client_secret:
            self.spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir).expanduser().resolve()

    @property
    def audio_format(self) -> AudioFormat:
        return AudioFormat(self.format)

    @property
    def has_spotify_credentials(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)

    def ydl_format_opts(self) -> dict:
        """Return yt-dlp format/postprocessor options derived from this config."""
        opts: dict = {}

        if self.format == "mp3":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(self.quality),
            }]
        elif self.format == "m4a":
            opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }]
        elif self.format == "flac":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "flac",
            }]
        elif self.format == "wav":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }]
        elif self.format == "ogg":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "vorbis",
            }]

        return opts

    @classmethod
    def from_env(cls) -> "Config":
        """Create a Config populated from environment variables."""
        kwargs = {}
        if val := os.environ.get("PYMUSIC_OUTPUT_DIR"):
            kwargs["output_dir"] = val
        if val := os.environ.get("PYMUSIC_FORMAT"):
            kwargs["format"] = val
        if val := os.environ.get("PYMUSIC_QUALITY"):
            kwargs["quality"] = int(val)
        return cls(**kwargs)
