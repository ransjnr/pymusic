"""Custom exceptions for pyMusic."""


class PyMusicError(Exception):
    """Base exception for all pyMusic errors."""


class DownloadError(PyMusicError):
    """Raised when a download fails."""

    def __init__(self, message: str, url: str = "", cause: Exception = None):
        self.url = url
        self.cause = cause
        super().__init__(message)


class UnsupportedURLError(PyMusicError):
    """Raised when a URL is not supported."""

    def __init__(self, url: str):
        self.url = url
        super().__init__(f"Unsupported URL: {url}")


class PlaylistError(PyMusicError):
    """Raised when playlist operations fail."""


class MetadataError(PyMusicError):
    """Raised when metadata operations fail."""


class ConfigurationError(PyMusicError):
    """Raised when configuration is invalid."""


class SpotifyAuthError(PyMusicError):
    """Raised when Spotify authentication fails."""

    def __init__(self, message: str = None):
        msg = message or (
            "Spotify credentials not found. Set SPOTIFY_CLIENT_ID and "
            "SPOTIFY_CLIENT_SECRET environment variables or pass them to Config."
        )
        super().__init__(msg)


class SearchError(PyMusicError):
    """Raised when a search operation fails."""

    def __init__(self, query: str, message: str = ""):
        self.query = query
        super().__init__(message or f"Search failed for query: {query!r}")


class FormatError(PyMusicError):
    """Raised when an unsupported audio format is requested."""

    def __init__(self, fmt: str):
        self.format = fmt
        super().__init__(
            f"Unsupported format: {fmt!r}. "
            "Supported formats: mp3, m4a, flac, wav, ogg"
        )
