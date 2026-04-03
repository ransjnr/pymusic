"""Tests for pymusic.utils."""
import pytest
from pymusic.utils import (
    detect_source,
    is_youtube_playlist,
    is_youtube_video,
    is_soundcloud_set,
    is_spotify_playlist,
    sanitize_filename,
    format_size,
    format_duration,
    extract_spotify_id,
    spotify_entity_type,
    build_output_path,
)


class TestDetectSource:
    def test_youtube_watch(self):
        assert detect_source("https://www.youtube.com/watch?v=abc123") == "youtube"

    def test_youtu_be(self):
        assert detect_source("https://youtu.be/abc123") == "youtube"

    def test_youtube_music(self):
        assert detect_source("https://music.youtube.com/watch?v=abc") == "youtube"

    def test_soundcloud(self):
        assert detect_source("https://soundcloud.com/artist/track") == "soundcloud"

    def test_soundcloud_on(self):
        assert detect_source("https://on.soundcloud.com/abc") == "soundcloud"

    def test_spotify(self):
        assert detect_source("https://open.spotify.com/track/abc") == "spotify"

    def test_bandcamp(self):
        assert detect_source("https://artist.bandcamp.com/track/song") == "bandcamp"

    def test_generic(self):
        assert detect_source("https://example.com/audio.mp3") == "generic"


class TestIsYouTubePlaylist:
    def test_playlist_url(self):
        assert is_youtube_playlist("https://www.youtube.com/playlist?list=PLxxx")

    def test_watch_url_is_not_playlist(self):
        assert not is_youtube_playlist("https://www.youtube.com/watch?v=abc")

    def test_watch_url_with_list_is_not_plain_playlist(self):
        # URL has both v and list — it's a video with a playlist context
        assert not is_youtube_playlist("https://www.youtube.com/watch?v=abc&list=PLxxx")

    def test_non_youtube_is_not_playlist(self):
        assert not is_youtube_playlist("https://soundcloud.com/artist/set")


class TestIsYoutubeVideo:
    def test_watch_url(self):
        assert is_youtube_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_youtu_be(self):
        assert is_youtube_video("https://youtu.be/dQw4w9WgXcQ")

    def test_playlist_only_is_not_video(self):
        assert not is_youtube_video("https://www.youtube.com/playlist?list=PLxxx")


class TestIsSoundCloudSet:
    def test_set_url(self):
        assert is_soundcloud_set("https://soundcloud.com/artist/sets/my-playlist")

    def test_track_url_not_set(self):
        assert not is_soundcloud_set("https://soundcloud.com/artist/track")


class TestIsSpotifyPlaylist:
    def test_playlist_url(self):
        assert is_spotify_playlist("https://open.spotify.com/playlist/abc")

    def test_album_url(self):
        assert is_spotify_playlist("https://open.spotify.com/album/abc")

    def test_track_url_not_playlist(self):
        assert not is_spotify_playlist("https://open.spotify.com/track/abc")


class TestSanitizeFilename:
    def test_removes_illegal_chars(self):
        result = sanitize_filename('File: "test" <bad>')
        assert '"' not in result
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result

    def test_preserves_normal_chars(self):
        assert sanitize_filename("Normal Song Name") == "Normal Song Name"

    def test_truncates_long_name(self):
        long_name = "x" * 300
        assert len(sanitize_filename(long_name)) <= 200

    def test_empty_string_returns_unknown(self):
        assert sanitize_filename("") == "unknown"

    def test_strips_leading_trailing_dots(self):
        result = sanitize_filename("...test...")
        assert not result.startswith(".")
        assert not result.endswith(".")


class TestFormatSize:
    def test_bytes(self):
        assert "B" in format_size(512)

    def test_kilobytes(self):
        assert "KB" in format_size(2048)

    def test_megabytes(self):
        assert "MB" in format_size(5 * 1024 * 1024)


class TestFormatDuration:
    def test_minutes_seconds(self):
        assert format_duration(185) == "3:05"

    def test_hours(self):
        assert format_duration(3661) == "1:01:01"

    def test_zero(self):
        assert format_duration(0) == "0:00"


class TestExtractSpotifyId:
    def test_track_id(self):
        url = "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"
        assert extract_spotify_id(url) == "4iV5W9uYEdYUVa79Axb7Rh"

    def test_playlist_id(self):
        url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        assert extract_spotify_id(url) == "37i9dQZF1DXcBWIGoYBM5M"

    def test_album_id(self):
        url = "https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3"
        assert extract_spotify_id(url) == "1DFixLWuPkv3KT3TnV35m3"

    def test_invalid_url_returns_none(self):
        assert extract_spotify_id("https://example.com/foo") is None


class TestSpotifyEntityType:
    def test_track(self):
        assert spotify_entity_type("https://open.spotify.com/track/abc") == "track"

    def test_album(self):
        assert spotify_entity_type("https://open.spotify.com/album/abc") == "album"

    def test_playlist(self):
        assert spotify_entity_type("https://open.spotify.com/playlist/abc") == "playlist"

    def test_artist(self):
        assert spotify_entity_type("https://open.spotify.com/artist/abc") == "artist"

    def test_unknown_returns_none(self):
        assert spotify_entity_type("https://example.com/foo") is None


class TestBuildOutputPath:
    def test_basic(self, tmp_path):
        path = build_output_path(tmp_path, "My Song", fmt="mp3")
        assert path.parent == tmp_path
        assert path.name == "My Song.mp3"

    def test_with_subdirs_artist_album(self, tmp_path):
        path = build_output_path(
            tmp_path, "My Song", artist="The Artist", album="The Album",
            fmt="flac", create_subdirs=True
        )
        assert "The Artist" in str(path)
        assert "The Album" in str(path)
        assert path.name == "My Song.flac"

    def test_directory_is_created(self, tmp_path):
        sub = tmp_path / "new_dir"
        build_output_path(sub, "Song", fmt="mp3")
        assert sub.exists()
