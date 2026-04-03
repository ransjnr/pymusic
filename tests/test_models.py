"""Tests for pymusic.models."""
import pytest
from pymusic.models import (
    AudioFormat, DownloadStatus, Playlist, SearchResult, Source, Track
)
from pymusic.exceptions import FormatError


class TestAudioFormat:
    def test_valid_formats(self):
        for fmt in ("mp3", "m4a", "flac", "wav", "ogg"):
            assert AudioFormat.from_string(fmt) == AudioFormat(fmt)

    def test_case_insensitive(self):
        assert AudioFormat.from_string("MP3") == AudioFormat.MP3
        assert AudioFormat.from_string("FLAC") == AudioFormat.FLAC

    def test_invalid_format_raises(self):
        with pytest.raises(FormatError):
            AudioFormat.from_string("aac")

    def test_format_values(self):
        assert AudioFormat.MP3.value == "mp3"
        assert AudioFormat.FLAC.value == "flac"


class TestTrack:
    def _make_track(self, **kwargs) -> Track:
        defaults = dict(url="https://youtube.com/watch?v=test", title="Test Song", artist="Test Artist")
        defaults.update(kwargs)
        return Track(**defaults)

    def test_display_name_with_artist_and_title(self):
        t = self._make_track()
        assert t.display_name == "Test Artist - Test Song"

    def test_display_name_title_only(self):
        t = self._make_track(artist="")
        assert t.display_name == "Test Song"

    def test_display_name_url_fallback(self):
        t = Track(url="https://youtube.com/watch?v=abc", title="", artist="")
        assert "youtube.com" in t.display_name

    def test_duration_str_minutes(self):
        t = self._make_track(duration=185.0)
        assert t.duration_str == "3:05"

    def test_duration_str_hours(self):
        t = self._make_track(duration=3661.0)
        assert t.duration_str == "1:01:01"

    def test_duration_str_unknown(self):
        t = self._make_track(duration=0)
        assert t.duration_str == "Unknown"

    def test_is_downloaded_false_by_default(self):
        t = self._make_track()
        assert not t.is_downloaded

    def test_is_downloaded_true_when_file_exists(self, tmp_path):
        f = tmp_path / "song.mp3"
        f.write_text("dummy")
        t = self._make_track(status=DownloadStatus.COMPLETED, file_path=str(f))
        assert t.is_downloaded

    def test_is_downloaded_false_when_file_missing(self):
        t = self._make_track(
            status=DownloadStatus.COMPLETED,
            file_path="/nonexistent/path/song.mp3"
        )
        assert not t.is_downloaded

    def test_repr(self):
        t = self._make_track()
        assert "Test Song" in repr(t)
        assert "Test Artist" in repr(t)


class TestPlaylist:
    def _make_playlist(self, num_tracks: int = 3) -> Playlist:
        tracks = [
            Track(url=f"https://yt.com/watch?v={i}", title=f"Track {i}", artist="Artist",
                  status=DownloadStatus.PENDING)
            for i in range(num_tracks)
        ]
        return Playlist(url="https://yt.com/playlist?list=test", title="Test Playlist", tracks=tracks)

    def test_total_tracks(self):
        pl = self._make_playlist(5)
        assert pl.total_tracks == 5

    def test_downloaded_tracks_empty_initially(self):
        pl = self._make_playlist(3)
        assert pl.downloaded_tracks == []

    def test_failed_tracks(self):
        pl = self._make_playlist(3)
        pl.tracks[1].status = DownloadStatus.FAILED
        assert len(pl.failed_tracks) == 1

    def test_duration(self):
        pl = self._make_playlist(3)
        for t in pl.tracks:
            t.duration = 60.0
        assert pl.duration == 180.0

    def test_repr(self):
        pl = self._make_playlist(2)
        assert "Test Playlist" in repr(pl)
        assert "2" in repr(pl)


class TestSearchResult:
    def test_display_name_with_artist(self):
        r = SearchResult(url="https://yt.com/watch?v=1", title="Song", artist="Artist")
        assert r.display_name == "Artist - Song"

    def test_display_name_without_artist(self):
        r = SearchResult(url="https://yt.com/watch?v=1", title="Song")
        assert r.display_name == "Song"

    def test_duration_str(self):
        r = SearchResult(url="https://yt.com/watch?v=1", title="Song", duration=245.0)
        assert r.duration_str == "4:05"

    def test_to_track(self):
        r = SearchResult(
            url="https://yt.com/watch?v=1",
            title="Song",
            artist="Artist",
            duration=180.0,
            source=Source.YOUTUBE,
        )
        track = r.to_track()
        assert isinstance(track, Track)
        assert track.title == "Song"
        assert track.artist == "Artist"
        assert track.url == r.url
