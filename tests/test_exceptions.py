"""Tests for pymusic.exceptions."""
import pytest
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


class TestExceptions:
    def test_download_error_carries_url(self):
        exc = DownloadError("failed", url="https://yt.com/watch?v=abc")
        assert exc.url == "https://yt.com/watch?v=abc"
        assert "failed" in str(exc)

    def test_download_error_carries_cause(self):
        cause = ValueError("root cause")
        exc = DownloadError("failed", cause=cause)
        assert exc.cause is cause

    def test_unsupported_url_error(self):
        exc = UnsupportedURLError("https://bad.com")
        assert "https://bad.com" in str(exc)
        assert exc.url == "https://bad.com"

    def test_spotify_auth_error_default_message(self):
        exc = SpotifyAuthError()
        assert "SPOTIFY_CLIENT_ID" in str(exc)

    def test_spotify_auth_error_custom_message(self):
        exc = SpotifyAuthError("custom message")
        assert "custom message" in str(exc)

    def test_search_error_carries_query(self):
        exc = SearchError("my query")
        assert exc.query == "my query"
        assert "my query" in str(exc)

    def test_format_error_carries_format(self):
        exc = FormatError("xyz")
        assert exc.format == "xyz"
        assert "xyz" in str(exc)

    def test_all_exceptions_are_pymusic_errors(self):
        for exc_class in (
            DownloadError, UnsupportedURLError, PlaylistError,
            MetadataError, ConfigurationError, SpotifyAuthError,
            SearchError, FormatError,
        ):
            exc = exc_class.__new__(exc_class)
            assert isinstance(exc, PyMusicError)
