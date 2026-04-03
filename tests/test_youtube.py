"""Tests for pymusic.youtube module."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from pymusic.config import Config
from pymusic.exceptions import DownloadError, SearchError
from pymusic.models import Playlist, SearchResult, Source, Track
from pymusic.youtube import (
    _info_to_track,
    get_playlist_info,
    get_track_info,
    search_youtube,
)


@pytest.fixture
def config(tmp_path) -> Config:
    return Config(output_dir=str(tmp_path), quiet=True)


SAMPLE_VIDEO_INFO = {
    "id": "dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
    "uploader": "Rick Astley",
    "artist": "Rick Astley",
    "album": "Whenever You Need Somebody",
    "duration": 212,
    "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "upload_date": "20091025",
    "view_count": 1_400_000_000,
}

SAMPLE_PLAYLIST_INFO = {
    "id": "PLtest",
    "title": "Test Playlist",
    "uploader": "Test User",
    "webpage_url": "https://www.youtube.com/playlist?list=PLtest",
    "thumbnail": "https://i.ytimg.com/vi/thumb.jpg",
    "entries": [
        {
            "id": "vid1",
            "title": "Song 1",
            "uploader": "Artist 1",
            "duration": 180,
            "url": "https://www.youtube.com/watch?v=vid1",
            "thumbnail": "https://i.ytimg.com/vi/vid1/thumb.jpg",
        },
        {
            "id": "vid2",
            "title": "Song 2",
            "uploader": "Artist 2",
            "duration": 240,
            "url": "https://www.youtube.com/watch?v=vid2",
            "thumbnail": "https://i.ytimg.com/vi/vid2/thumb.jpg",
        },
    ],
}


class TestInfoToTrack:
    def test_basic_conversion(self):
        track = _info_to_track(SAMPLE_VIDEO_INFO)
        assert track.title == SAMPLE_VIDEO_INFO["title"]
        assert track.artist == "Rick Astley"
        assert track.album == "Whenever You Need Somebody"
        assert track.duration == 212.0
        assert track.source == Source.YOUTUBE

    def test_year_extracted_from_upload_date(self):
        info = {**SAMPLE_VIDEO_INFO, "upload_date": "20151231", "release_year": None}
        track = _info_to_track(info)
        assert track.year == "2015"

    def test_release_year_takes_priority(self):
        info = {**SAMPLE_VIDEO_INFO, "release_year": 2009, "upload_date": "20151231"}
        track = _info_to_track(info)
        assert track.year == "2009"

    def test_track_number_and_total(self):
        track = _info_to_track(SAMPLE_VIDEO_INFO, playlist_index=3, total=10)
        assert track.track_number == 3
        assert track.total_tracks == 10

    def test_thumbnail_url(self):
        track = _info_to_track(SAMPLE_VIDEO_INFO)
        assert "ytimg.com" in track.thumbnail_url


class TestGetTrackInfo:
    def test_returns_track(self, config):
        with patch("pymusic.youtube.extract_info", return_value=SAMPLE_VIDEO_INFO):
            track = get_track_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", config)
            assert isinstance(track, Track)
            assert track.title == SAMPLE_VIDEO_INFO["title"]

    def test_raises_on_extract_failure(self, config):
        with patch("pymusic.youtube.extract_info", side_effect=DownloadError("failed")):
            with pytest.raises(DownloadError):
                get_track_info("https://www.youtube.com/watch?v=bad", config)


class TestGetPlaylistInfo:
    def test_returns_playlist(self, config):
        with patch("pymusic.youtube.extract_info", return_value=SAMPLE_PLAYLIST_INFO):
            pl = get_playlist_info("https://www.youtube.com/playlist?list=PLtest", config)
            assert isinstance(pl, Playlist)
            assert pl.title == "Test Playlist"
            assert pl.total_tracks == 2

    def test_track_urls_are_full_youtube_urls(self, config):
        with patch("pymusic.youtube.extract_info", return_value=SAMPLE_PLAYLIST_INFO):
            pl = get_playlist_info("https://www.youtube.com/playlist?list=PLtest", config)
            for track in pl.tracks:
                assert track.url.startswith("https://")

    def test_track_numbers_assigned(self, config):
        with patch("pymusic.youtube.extract_info", return_value=SAMPLE_PLAYLIST_INFO):
            pl = get_playlist_info("https://www.youtube.com/playlist?list=PLtest", config)
            numbers = [t.track_number for t in pl.tracks]
            assert numbers == [1, 2]

    def test_empty_playlist(self, config):
        empty_info = {**SAMPLE_PLAYLIST_INFO, "entries": []}
        with patch("pymusic.youtube.extract_info", return_value=empty_info):
            pl = get_playlist_info("https://www.youtube.com/playlist?list=PLtest", config)
            assert pl.total_tracks == 0


class TestSearchYouTube:
    SEARCH_RESULTS = {
        "entries": [
            {
                "id": "result1",
                "title": "Never Gonna Give You Up",
                "uploader": "Rick Astley",
                "duration": 212,
                "url": "https://www.youtube.com/watch?v=result1",
                "thumbnail": "https://i.ytimg.com/vi/result1/thumb.jpg",
                "view_count": 1_000_000,
            },
        ]
    }

    def test_returns_search_results(self, config):
        with patch("pymusic.youtube.extract_info", return_value=self.SEARCH_RESULTS):
            results = search_youtube("rick astley", config, limit=5)
            assert len(results) == 1
            assert isinstance(results[0], SearchResult)
            assert results[0].title == "Never Gonna Give You Up"

    def test_raises_search_error_on_failure(self, config):
        with patch("pymusic.youtube.extract_info", side_effect=DownloadError("fail")):
            with pytest.raises(SearchError):
                search_youtube("impossible query", config)

    def test_empty_results(self, config):
        with patch("pymusic.youtube.extract_info", return_value={"entries": []}):
            results = search_youtube("nothing here", config)
            assert results == []

    def test_result_source_is_youtube(self, config):
        with patch("pymusic.youtube.extract_info", return_value=self.SEARCH_RESULTS):
            results = search_youtube("rick astley", config)
            assert all(r.source == Source.YOUTUBE for r in results)
