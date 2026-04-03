"""Tests for pymusic.config."""
import os
import pytest
from pymusic.config import Config
from pymusic.exceptions import ConfigurationError


class TestConfig:
    def test_defaults(self):
        c = Config()
        assert c.format == "mp3"
        assert c.quality == 192
        assert c.embed_metadata is True
        assert c.embed_thumbnail is True
        assert c.retries == 3

    def test_custom_format(self):
        c = Config(format="flac")
        assert c.format == "flac"

    def test_invalid_format_raises(self):
        with pytest.raises(ConfigurationError, match="Invalid format"):
            Config(format="aac")

    def test_invalid_quality_raises(self):
        with pytest.raises(ConfigurationError, match="Invalid quality"):
            Config(format="mp3", quality=999)

    def test_invalid_playlist_start_raises(self):
        with pytest.raises(ConfigurationError, match="playlist_start"):
            Config(playlist_start=0)

    def test_invalid_playlist_range_raises(self):
        with pytest.raises(ConfigurationError, match="playlist_end"):
            Config(playlist_start=5, playlist_end=3)

    def test_output_path(self, tmp_path):
        c = Config(output_dir=str(tmp_path))
        assert c.output_path == tmp_path

    def test_has_spotify_credentials_false(self):
        c = Config()
        c.spotify_client_id = None
        c.spotify_client_secret = None
        assert not c.has_spotify_credentials

    def test_has_spotify_credentials_true(self):
        c = Config(spotify_client_id="id", spotify_client_secret="secret")
        assert c.has_spotify_credentials

    def test_env_spotify_credentials(self, monkeypatch):
        monkeypatch.setenv("SPOTIFY_CLIENT_ID", "env_id")
        monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "env_secret")
        c = Config()
        assert c.spotify_client_id == "env_id"
        assert c.spotify_client_secret == "env_secret"

    def test_from_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PYMUSIC_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("PYMUSIC_FORMAT", "flac")
        monkeypatch.setenv("PYMUSIC_QUALITY", "256")
        c = Config.from_env()
        assert c.format == "flac"
        assert c.quality == 256
        assert str(tmp_path) in str(c.output_path)

    def test_ydl_format_opts_mp3(self):
        c = Config(format="mp3", quality=320)
        opts = c.ydl_format_opts()
        assert opts["format"] == "bestaudio/best"
        pp = opts["postprocessors"][0]
        assert pp["preferredcodec"] == "mp3"
        assert pp["preferredquality"] == "320"

    def test_ydl_format_opts_flac(self):
        c = Config(format="flac")
        opts = c.ydl_format_opts()
        pp = opts["postprocessors"][0]
        assert pp["preferredcodec"] == "flac"

    def test_ydl_format_opts_m4a(self):
        c = Config(format="m4a")
        opts = c.ydl_format_opts()
        pp = opts["postprocessors"][0]
        assert pp["preferredcodec"] == "m4a"
