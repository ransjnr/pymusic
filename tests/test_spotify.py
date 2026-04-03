"""Tests for pymusic.spotify module."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from pymusic.config import Config
from pymusic.exceptions import SpotifyAuthError, DownloadError
from pymusic.models import Playlist, Source, Track
from pymusic.spotify import _spotify_track_to_track, _pick_best_match, get_track_info


@pytest.fixture
def config_with_spotify(tmp_path) -> Config:
    return Config(
        output_dir=str(tmp_path),
        spotify_client_id="test_id",
        spotify_client_secret="test_secret",
        quiet=True,
    )


@pytest.fixture
def config_no_spotify(tmp_path) -> Config:
    c = Config(output_dir=str(tmp_path), quiet=True)
    c.spotify_client_id = None
    c.spotify_client_secret = None
    return c


SAMPLE_SP_TRACK = {
    "id": "4iV5W9uYEdYUVa79Axb7Rh",
    "name": "Never Gonna Give You Up",
    "artists": [{"name": "Rick Astley"}],
    "album": {
        "name": "Whenever You Need Somebody",
        "artists": [{"name": "Rick Astley"}],
        "release_date": "1987-07-27",
        "images": [
            {"url": "https://i.scdn.co/image/large.jpg", "height": 640},
            {"url": "https://i.scdn.co/image/small.jpg", "height": 300},
        ],
    },
    "duration_ms": 212000,
    "track_number": 1,
    "external_urls": {"spotify": "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"},
}


class TestSpotifyTrackToTrack:
    def test_basic_conversion(self):
        track = _spotify_track_to_track(SAMPLE_SP_TRACK)
        assert track.title == "Never Gonna Give You Up"
        assert track.artist == "Rick Astley"
        assert track.album == "Whenever You Need Somebody"
        assert track.year == "1987"
        assert track.source == Source.SPOTIFY

    def test_duration_converted_from_ms(self):
        track = _spotify_track_to_track(SAMPLE_SP_TRACK)
        assert abs(track.duration - 212.0) < 0.1

    def test_multiple_artists_joined(self):
        info = dict(SAMPLE_SP_TRACK)
        info["artists"] = [{"name": "Artist A"}, {"name": "Artist B"}]
        track = _spotify_track_to_track(info)
        assert track.artist == "Artist A, Artist B"

    def test_thumbnail_largest_image_selected(self):
        track = _spotify_track_to_track(SAMPLE_SP_TRACK)
        assert track.thumbnail_url == "https://i.scdn.co/image/large.jpg"

    def test_spotify_id_in_extra(self):
        track = _spotify_track_to_track(SAMPLE_SP_TRACK)
        assert track.extra.get("spotify_id") == "4iV5W9uYEdYUVa79Axb7Rh"

    def test_no_artists_returns_empty_string(self):
        info = {**SAMPLE_SP_TRACK, "artists": []}
        track = _spotify_track_to_track(info)
        assert track.artist == ""


class TestPickBestMatch:
    def _make_results(self, durations):
        from pymusic.models import SearchResult
        return [
            SearchResult(
                url=f"https://yt.com/watch?v={i}",
                title=f"Result {i}",
                duration=d,
                source=Source.YOUTUBE,
            )
            for i, d in enumerate(durations)
        ]

    def _make_track(self, duration: float) -> Track:
        return Track(url="https://open.spotify.com/track/abc", title="Song", duration=duration)

    def test_picks_closest_duration(self):
        results = self._make_results([200, 212, 220])
        track = self._make_track(212.0)
        best = _pick_best_match(results, track)
        assert best.duration == 212

    def test_with_no_duration_picks_first(self):
        results = self._make_results([200, 212])
        track = self._make_track(0)
        best = _pick_best_match(results, track)
        assert best == results[0]

    def test_raises_on_empty_results(self):
        from pymusic.exceptions import SearchError
        track = self._make_track(180.0)
        with pytest.raises(SearchError):
            _pick_best_match([], track)


class TestGetTrackInfoNoCredentials:
    def test_raises_spotify_auth_error_without_credentials(self, config_no_spotify):
        with pytest.raises(SpotifyAuthError):
            get_track_info("https://open.spotify.com/track/abc", config_no_spotify)


class TestGetTrackInfo:
    def test_returns_track(self, config_with_spotify):
        mock_sp = MagicMock()
        mock_sp.track.return_value = SAMPLE_SP_TRACK

        with patch("pymusic.spotify._get_spotify_client", return_value=mock_sp):
            with patch("pymusic.spotify.extract_spotify_id", return_value="4iV5W9uYEdYUVa79Axb7Rh"):
                track = get_track_info(
                    "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh",
                    config_with_spotify,
                )
                assert isinstance(track, Track)
                assert track.title == "Never Gonna Give You Up"
                assert track.source == Source.SPOTIFY

    def test_raises_when_id_not_extractable(self, config_with_spotify):
        mock_sp = MagicMock()
        with patch("pymusic.spotify._get_spotify_client", return_value=mock_sp):
            with patch("pymusic.spotify.extract_spotify_id", return_value=None):
                with pytest.raises(DownloadError):
                    get_track_info("https://bad-url.com/no-id", config_with_spotify)
