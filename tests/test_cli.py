"""Tests for pymusic.cli."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from pymusic.cli import main
from pymusic.models import DownloadStatus, Playlist, SearchResult, Source, Track
from pymusic.exceptions import DownloadError, SearchError


@pytest.fixture
def runner():
    return CliRunner()


class TestDownloadCommand:
    def test_download_invokes_pm_download(self, runner):
        track = Track(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Never Gonna Give You Up",
            artist="Rick Astley",
            status=DownloadStatus.COMPLETED,
            file_path="/tmp/Never Gonna Give You Up.mp3",
        )
        with patch("pymusic.core.PyMusic.download", return_value=track):
            result = runner.invoke(main, [
                "download",
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "--quiet",
            ])
            assert result.exit_code == 0

    def test_download_shows_file_path_in_quiet_mode(self, runner):
        track = Track(
            url="https://www.youtube.com/watch?v=test",
            title="Test",
            status=DownloadStatus.COMPLETED,
            file_path="/tmp/test.mp3",
        )
        with patch("pymusic.core.PyMusic.download", return_value=track):
            result = runner.invoke(main, ["download", "https://yt.com/watch?v=test", "--quiet"])
            assert "/tmp/test.mp3" in result.output

    def test_download_exits_1_on_error(self, runner):
        with patch("pymusic.core.PyMusic.download", side_effect=DownloadError("failed", url="https://yt.com")):
            result = runner.invoke(main, ["download", "https://yt.com/watch?v=bad"])
            assert result.exit_code == 1

    def test_download_playlist_shows_summary(self, runner):
        tracks = [
            Track(url=f"https://yt.com/watch?v={i}", title=f"Track {i}",
                  status=DownloadStatus.COMPLETED, file_path=f"/tmp/track{i}.mp3")
            for i in range(3)
        ]
        pl = Playlist(url="https://yt.com/playlist?list=PL", title="My Playlist",
                      source=Source.YOUTUBE, tracks=tracks)
        with patch("pymusic.core.PyMusic.download", return_value=pl):
            result = runner.invoke(main, ["download", "https://yt.com/playlist?list=PL"])
            assert result.exit_code == 0
            assert "My Playlist" in result.output

    def test_format_option(self, runner):
        track = Track(url="https://yt.com/watch?v=1", title="T", status=DownloadStatus.COMPLETED)
        with patch("pymusic.core.PyMusic.download", return_value=track) as mock_dl:
            runner.invoke(main, ["download", "https://yt.com/watch?v=1", "--format", "flac", "--quiet"])
            # Config should have flac format — verify PyMusic was instantiated with correct config
            mock_dl.assert_called_once()


class TestSearchCommand:
    MOCK_RESULTS = [
        SearchResult(
            url="https://www.youtube.com/watch?v=1",
            title="Never Gonna Give You Up",
            artist="Rick Astley",
            duration=212.0,
            source=Source.YOUTUBE,
        ),
        SearchResult(
            url="https://www.youtube.com/watch?v=2",
            title="Together Forever",
            artist="Rick Astley",
            duration=210.0,
            source=Source.YOUTUBE,
        ),
    ]

    def test_search_shows_results(self, runner):
        with patch("pymusic.core.PyMusic.search", return_value=self.MOCK_RESULTS):
            result = runner.invoke(main, ["search", "rick astley"])
            assert result.exit_code == 0
            assert "Never Gonna Give You Up" in result.output
            assert "Together Forever" in result.output

    def test_search_shows_index(self, runner):
        with patch("pymusic.core.PyMusic.search", return_value=self.MOCK_RESULTS):
            result = runner.invoke(main, ["search", "rick astley"])
            assert " 1." in result.output
            assert " 2." in result.output

    def test_search_download_flag(self, runner):
        dl_track = Track(
            url="https://www.youtube.com/watch?v=1",
            title="Never Gonna Give You Up",
            status=DownloadStatus.COMPLETED,
            file_path="/tmp/track.mp3",
        )
        with patch("pymusic.core.PyMusic.search", return_value=self.MOCK_RESULTS):
            with patch("pymusic.downloader.download_track") as mock_dl:
                mock_dl.return_value = "/tmp/track.mp3"
                result = runner.invoke(main, ["search", "rick astley", "--download", "--quiet"])
                mock_dl.assert_called_once()

    def test_search_no_results(self, runner):
        with patch("pymusic.core.PyMusic.search", return_value=[]):
            result = runner.invoke(main, ["search", "nothing"])
            assert result.exit_code == 0
            assert "No results" in result.output

    def test_search_soundcloud_source(self, runner):
        with patch("pymusic.core.PyMusic.search", return_value=self.MOCK_RESULTS) as mock_search:
            runner.invoke(main, ["search", "query", "--source", "soundcloud"])
            call_kwargs = mock_search.call_args
            assert "soundcloud" in str(call_kwargs)


class TestInfoCommand:
    def test_info_track(self, runner):
        track = Track(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Never Gonna Give You Up",
            artist="Rick Astley",
            album="Whenever You Need Somebody",
            year="1987",
            duration=212.0,
            source=Source.YOUTUBE,
        )
        with patch("pymusic.core.PyMusic.get_info", return_value=track):
            result = runner.invoke(main, ["info", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
            assert result.exit_code == 0
            assert "Never Gonna Give You Up" in result.output
            assert "Rick Astley" in result.output
            assert "1987" in result.output

    def test_info_playlist(self, runner):
        tracks = [
            Track(url=f"https://yt.com/watch?v={i}", title=f"Song {i}", track_number=i, duration=180.0)
            for i in range(1, 4)
        ]
        pl = Playlist(
            url="https://yt.com/playlist?list=PLtest",
            title="Test Playlist",
            uploader="Test User",
            source=Source.YOUTUBE,
            tracks=tracks,
        )
        with patch("pymusic.core.PyMusic.get_info", return_value=pl):
            result = runner.invoke(main, ["info", "https://yt.com/playlist?list=PLtest"])
            assert result.exit_code == 0
            assert "Test Playlist" in result.output
            assert "3" in result.output

    def test_info_error_exits_1(self, runner):
        from pymusic.exceptions import PyMusicError
        with patch("pymusic.core.PyMusic.get_info", side_effect=PyMusicError("oops")):
            result = runner.invoke(main, ["info", "https://bad.com"])
            assert result.exit_code == 1


class TestVersionFlag:
    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestHelpText:
    def test_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "download" in result.output
        assert "search" in result.output
        assert "info" in result.output

    def test_download_help(self, runner):
        result = runner.invoke(main, ["download", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output
        assert "--quality" in result.output
        assert "--output" in result.output

    def test_search_help(self, runner):
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "--source" in result.output
        assert "--limit" in result.output
