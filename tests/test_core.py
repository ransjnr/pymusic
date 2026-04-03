"""Tests for pymusic.core (PyMusic API class)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from pymusic import PyMusic
from pymusic.config import Config
from pymusic.models import (
    DownloadStatus, Playlist, SearchResult, Source, Track
)


@pytest.fixture
def pm(tmp_path) -> PyMusic:
    return PyMusic(output_dir=str(tmp_path), quiet=True)


@pytest.fixture
def pm_verbose(tmp_path) -> PyMusic:
    return PyMusic(output_dir=str(tmp_path), verbose=True, quiet=False)


class TestPyMusicInit:
    def test_default_format(self, tmp_path):
        pm = PyMusic(output_dir=str(tmp_path), quiet=True)
        assert pm.config.format == "mp3"

    def test_custom_format(self, tmp_path):
        pm = PyMusic(output_dir=str(tmp_path), format="flac", quiet=True)
        assert pm.config.format == "flac"

    def test_custom_config(self, tmp_path):
        config = Config(output_dir=str(tmp_path), format="wav")
        pm = PyMusic(config=config)
        assert pm.config.format == "wav"

    def test_output_dir_property(self, tmp_path):
        pm = PyMusic(output_dir=str(tmp_path), quiet=True)
        assert pm.output_dir == tmp_path

    def test_set_format(self, pm):
        pm.set_format("flac")
        assert pm.config.format == "flac"

    def test_set_quality(self, pm):
        pm.set_quality(320)
        assert pm.config.quality == 320


class TestDownloadRouting:
    """Test that download() routes to the correct source module."""

    def test_routes_youtube_single(self, pm):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        with patch("pymusic.youtube.download_single") as mock_dl:
            mock_dl.return_value = Track(url=url, title="Test", source=Source.YOUTUBE)
            result = pm.download(url)
            mock_dl.assert_called_once()
            assert isinstance(result, Track)

    def test_routes_youtube_playlist(self, pm):
        url = "https://www.youtube.com/playlist?list=PLxxxxx"
        with patch("pymusic.youtube.download_playlist") as mock_dl:
            mock_dl.return_value = Playlist(url=url, title="My List", source=Source.YOUTUBE)
            result = pm.download(url)
            mock_dl.assert_called_once()
            assert isinstance(result, Playlist)

    def test_routes_soundcloud_track(self, pm):
        url = "https://soundcloud.com/artist/track"
        with patch("pymusic.soundcloud.download_track") as mock_dl:
            mock_dl.return_value = Track(url=url, title="SC Track", source=Source.SOUNDCLOUD)
            result = pm.download(url)
            mock_dl.assert_called_once()

    def test_routes_soundcloud_set(self, pm):
        url = "https://soundcloud.com/artist/sets/my-set"
        with patch("pymusic.soundcloud.download_set") as mock_dl:
            mock_dl.return_value = Playlist(url=url, title="SC Set", source=Source.SOUNDCLOUD)
            result = pm.download(url)
            mock_dl.assert_called_once()

    def test_routes_spotify_track(self, pm):
        url = "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"
        with patch("pymusic.spotify.download_track") as mock_dl:
            mock_dl.return_value = Track(url=url, title="SP Track", source=Source.SPOTIFY)
            result = pm.download(url)
            mock_dl.assert_called_once()

    def test_routes_spotify_playlist(self, pm):
        url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        with patch("pymusic.spotify.download_playlist") as mock_dl:
            mock_dl.return_value = Playlist(url=url, title="SP PL", source=Source.SPOTIFY)
            result = pm.download(url)
            mock_dl.assert_called_once()

    def test_routes_generic_url(self, pm):
        url = "https://bandcamp.com/artist/track"
        with patch("pymusic.generic.download_url") as mock_dl:
            mock_dl.return_value = Track(url=url, title="Bandcamp Track", source=Source.BANDCAMP)
            result = pm.download(url)
            mock_dl.assert_called_once()


class TestSearch:
    def test_search_youtube(self, pm):
        mock_results = [
            SearchResult(url="https://yt.com/watch?v=1", title="Song 1", source=Source.YOUTUBE),
            SearchResult(url="https://yt.com/watch?v=2", title="Song 2", source=Source.YOUTUBE),
        ]
        with patch("pymusic.youtube.search_youtube", return_value=mock_results) as mock_search:
            results = pm.search("test query", source="youtube", limit=5)
            mock_search.assert_called_once_with("test query", pm.config, 5)
            assert len(results) == 2

    def test_search_soundcloud(self, pm):
        mock_results = [
            SearchResult(url="https://soundcloud.com/artist/track", title="SC Song", source=Source.SOUNDCLOUD),
        ]
        with patch("pymusic.soundcloud.search_soundcloud", return_value=mock_results) as mock_search:
            results = pm.search("test", source="soundcloud", limit=3)
            mock_search.assert_called_once_with("test", pm.config, 3)
            assert results[0].source == Source.SOUNDCLOUD

    def test_search_defaults_to_youtube(self, pm):
        with patch("pymusic.youtube.search_youtube", return_value=[]) as mock_search:
            pm.search("query")
            mock_search.assert_called_once()

    def test_search_and_download(self, pm):
        track = Track(url="https://yt.com/watch?v=1", title="Song", source=Source.YOUTUBE,
                      status=DownloadStatus.COMPLETED)
        search_result = SearchResult(url="https://yt.com/watch?v=1", title="Song", source=Source.YOUTUBE)

        with patch("pymusic.youtube.search_youtube", return_value=[search_result]):
            with patch("pymusic.downloader.download_track") as mock_dl:
                mock_dl.return_value = "/tmp/Song.mp3"
                result = pm.search_and_download("test query")
                mock_dl.assert_called_once()

    def test_search_and_download_no_results_raises(self, pm):
        from pymusic.exceptions import SearchError
        with patch("pymusic.youtube.search_youtube", return_value=[]):
            with pytest.raises(SearchError):
                pm.search_and_download("impossible query xyz")


class TestGetInfo:
    def test_get_info_youtube_video(self, pm):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        expected = Track(url=url, title="Never Gonna Give You Up", artist="Rick Astley")
        with patch("pymusic.youtube.get_track_info", return_value=expected):
            result = pm.get_info(url)
            assert isinstance(result, Track)
            assert result.title == "Never Gonna Give You Up"

    def test_get_info_youtube_playlist(self, pm):
        url = "https://www.youtube.com/playlist?list=PLxxxxx"
        expected = Playlist(url=url, title="My Playlist")
        with patch("pymusic.youtube.get_playlist_info", return_value=expected):
            result = pm.get_info(url)
            assert isinstance(result, Playlist)
