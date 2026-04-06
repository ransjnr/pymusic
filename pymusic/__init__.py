"""pymusic-downloader — Download music from YouTube, SoundCloud, Spotify, and more."""

from pymusic.core import PyMusic
from pymusic.config import Config
from pymusic.models import (
    AudioFormat,
    DownloadResult,
    DownloadStatus,
    Playlist,
    SearchResult,
    Source,
    Track,
)
from pymusic.exceptions import (
    PyMusicError,
    DownloadError,
    UnsupportedURLError,
    PlaylistError,
    MetadataError,
    ConfigurationError,
    SpotifyAuthError,
    SearchError,
    FormatError,
)

__version__ = "0.1.4"
__author__ = "pyMusic Contributors"
__license__ = "MIT"
__package_name__ = "pymusic-downloader"
__url__ = "https://github.com/ransjnr/pymusic"

__all__ = [
    # Main class
    "PyMusic",
    # Config
    "Config",
    # Models
    "Track",
    "Playlist",
    "SearchResult",
    "DownloadResult",
    "AudioFormat",
    "Source",
    "DownloadStatus",
    # Exceptions
    "PyMusicError",
    "DownloadError",
    "UnsupportedURLError",
    "PlaylistError",
    "MetadataError",
    "ConfigurationError",
    "SpotifyAuthError",
    "SearchError",
    "FormatError",
]
