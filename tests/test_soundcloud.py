"""Tests for pymusic.soundcloud module."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from pymusic.config import Config
from pymusic.exceptions import DownloadError, SearchError
from pymusic.models import Playlist, SearchResult, Source, Track
from pymusic.soundcloud import _info_to_track, get_track_info, get_set_info, search_soundcloud


@pytest.fixture
def config(tmp_path) -> Config:
    return Config(output_dir=str(tmp_path), quiet=True)


SAMPLE_TRACK_INFO = {
    "id": "sc_12345",
    "title": "Levels",
    "uploader": "Avicii",
    "artist": "Avicii",
    "album": "",
    "duration": 323,
    "webpage_url": "https://soundcloud.com/avicii/levels",
    "thumbnail": "https://i1.sndcdn.com/artworks/levels.jpg",
    "upload_date": "20111028",
    "genre": "Electronic",
}

SAMPLE_SET_INFO = {
    "id": "set_abc",
    "title": "My SoundCloud Set",
    "uploader": "DJ Test",
    "webpage_url": "https://soundcloud.com/djtest/sets/my-set",
    "thumbnail": "https://i1.sndcdn.com/artworks/set.jpg",
    "entries": [
        {
            "id": "t1",
            "title": "Track One",
            "uploader": "Artist A",
            "duration": 200,
            "url": "https://soundcloud.com/artist-a/track-one",
            "thumbnail": "https://i1.sndcdn.com/artworks/t1.jpg",
        },
        {
            "id": "t2",
            "title": "Track Two",
            "uploader": "Artist B",
            "duration": 180,
            "url": "https://soundcloud.com/artist-b/track-two",
            "thumbnail": "https://i1.sndcdn.com/artworks/t2.jpg",
        },
    ],
}


class TestInfoToTrack:
    def test_basic_conversion(self):
        track = _info_to_track(SAMPLE_TRACK_INFO)
        assert track.title == "Levels"
        assert track.artist == "Avicii"
        assert track.duration == 323.0
        assert track.source == Source.SOUNDCLOUD
        assert track.genre == "Electronic"

    def test_year_from_upload_date(self):
        track = _info_to_track(SAMPLE_TRACK_INFO)
        assert track.year == "2011"


class TestGetTrackInfo:
    def test_returns_track(self, config):
        with patch("pymusic.soundcloud.extract_info", return_value=SAMPLE_TRACK_INFO):
            track = get_track_info("https://soundcloud.com/avicii/levels", config)
            assert isinstance(track, Track)
            assert track.title == "Levels"

    def test_raises_on_failure(self, config):
        with patch("pymusic.soundcloud.extract_info", side_effect=DownloadError("fail")):
            with pytest.raises(DownloadError):
                get_track_info("https://soundcloud.com/bad/url", config)


class TestGetSetInfo:
    def test_returns_playlist(self, config):
        with patch("pymusic.soundcloud.extract_info", return_value=SAMPLE_SET_INFO):
            pl = get_set_info("https://soundcloud.com/djtest/sets/my-set", config)
            assert isinstance(pl, Playlist)
            assert pl.title == "My SoundCloud Set"
            assert pl.total_tracks == 2
            assert pl.source == Source.SOUNDCLOUD

    def test_track_numbers_assigned(self, config):
        with patch("pymusic.soundcloud.extract_info", return_value=SAMPLE_SET_INFO):
            pl = get_set_info("https://soundcloud.com/djtest/sets/my-set", config)
            assert [t.track_number for t in pl.tracks] == [1, 2]

    def test_all_tracks_have_soundcloud_source(self, config):
        with patch("pymusic.soundcloud.extract_info", return_value=SAMPLE_SET_INFO):
            pl = get_set_info("https://soundcloud.com/djtest/sets/my-set", config)
            assert all(t.source == Source.SOUNDCLOUD for t in pl.tracks)


class TestSearchSoundCloud:
    SEARCH_RESULTS = {
        "entries": [
            {
                "title": "Levels",
                "uploader": "Avicii",
                "duration": 323,
                "url": "https://soundcloud.com/avicii/levels",
                "thumbnail": "https://i1.sndcdn.com/artworks/levels.jpg",
            },
        ]
    }

    def test_returns_results(self, config):
        with patch("pymusic.soundcloud.extract_info", return_value=self.SEARCH_RESULTS):
            results = search_soundcloud("avicii levels", config, limit=5)
            assert len(results) == 1
            assert isinstance(results[0], SearchResult)
            assert results[0].title == "Levels"

    def test_source_is_soundcloud(self, config):
        with patch("pymusic.soundcloud.extract_info", return_value=self.SEARCH_RESULTS):
            results = search_soundcloud("avicii", config)
            assert all(r.source == Source.SOUNDCLOUD for r in results)

    def test_raises_on_failure(self, config):
        with patch("pymusic.soundcloud.extract_info", side_effect=DownloadError("fail")):
            with pytest.raises(SearchError):
                search_soundcloud("query", config)
