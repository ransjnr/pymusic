"""Tests for pymusic.downloader."""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from pymusic.config import Config
from pymusic.downloader import build_ydl_opts, ProgressHook, _find_output_file
from pymusic.exceptions import DownloadError
from pymusic.models import DownloadStatus, Source, Track


@pytest.fixture
def config(tmp_path) -> Config:
    return Config(output_dir=str(tmp_path), format="mp3", quality=192)


class TestBuildYdlOpts:
    def test_returns_dict(self, config):
        opts = build_ydl_opts(config, "/tmp/%(id)s.%(ext)s")
        assert isinstance(opts, dict)

    def test_mp3_postprocessor(self, config):
        opts = build_ydl_opts(config, "/tmp/out.%(ext)s")
        pps = opts.get("postprocessors", [])
        codecs = [p.get("preferredcodec") for p in pps]
        assert "mp3" in codecs

    def test_flac_postprocessor(self, tmp_path):
        config = Config(output_dir=str(tmp_path), format="flac")
        opts = build_ydl_opts(config, "/tmp/out.%(ext)s")
        pps = opts.get("postprocessors", [])
        codecs = [p.get("preferredcodec") for p in pps]
        assert "flac" in codecs

    def test_metadata_postprocessor_added_when_embed_true(self, config):
        opts = build_ydl_opts(config, "/tmp/out.%(ext)s")
        keys = [p["key"] for p in opts.get("postprocessors", [])]
        assert "FFmpegMetadata" in keys

    def test_thumbnail_postprocessor_added(self, config):
        opts = build_ydl_opts(config, "/tmp/out.%(ext)s")
        keys = [p["key"] for p in opts.get("postprocessors", [])]
        assert "EmbedThumbnail" in keys

    def test_no_metadata_when_embed_false(self, tmp_path):
        config = Config(output_dir=str(tmp_path), embed_metadata=False, embed_thumbnail=False)
        opts = build_ydl_opts(config, "/tmp/out.%(ext)s")
        keys = [p.get("key") for p in opts.get("postprocessors", [])]
        assert "FFmpegMetadata" not in keys

    def test_rate_limit_added(self, tmp_path):
        config = Config(output_dir=str(tmp_path), rate_limit="500K")
        opts = build_ydl_opts(config, "/tmp/out.%(ext)s")
        assert opts.get("ratelimit") == "500K"

    def test_proxy_added(self, tmp_path):
        config = Config(output_dir=str(tmp_path), proxy="socks5://127.0.0.1:1080")
        opts = build_ydl_opts(config, "/tmp/out.%(ext)s")
        assert opts.get("proxy") == "socks5://127.0.0.1:1080"

    def test_extra_opts_merged(self, config):
        opts = build_ydl_opts(config, "/tmp/out.%(ext)s", extra_opts={"my_key": "my_value"})
        assert opts["my_key"] == "my_value"

    def test_overwrite_false(self, config):
        opts = build_ydl_opts(config, "/tmp/out.%(ext)s")
        assert opts["nooverwrites"] is True

    def test_overwrite_true(self, tmp_path):
        config = Config(output_dir=str(tmp_path), overwrite=True)
        opts = build_ydl_opts(config, "/tmp/out.%(ext)s")
        assert opts["nooverwrites"] is False


class TestProgressHook:
    def _make_track(self) -> Track:
        return Track(url="https://yt.com/watch?v=test", title="Test")

    def test_downloading_status_set(self):
        track = self._make_track()
        hook = ProgressHook(track)
        hook({"status": "downloading", "downloaded_bytes": 1000, "total_bytes": 5000})
        assert track.status == DownloadStatus.DOWNLOADING

    def test_finished_sets_processing(self):
        track = self._make_track()
        hook = ProgressHook(track)
        hook({"status": "finished"})
        assert track.status == DownloadStatus.PROCESSING

    def test_error_sets_failed(self):
        track = self._make_track()
        hook = ProgressHook(track)
        hook({"status": "error"})
        assert track.status == DownloadStatus.FAILED

    def test_callback_called_on_downloading(self):
        track = self._make_track()
        callback = MagicMock()
        hook = ProgressHook(track, callback)
        hook({"status": "downloading", "downloaded_bytes": 500, "total_bytes": 1000, "speed": 50})
        callback.assert_called_once_with(track, 500, 1000, 50)

    def test_no_callback_no_error(self):
        track = self._make_track()
        hook = ProgressHook(track, None)
        hook({"status": "downloading", "downloaded_bytes": 500, "total_bytes": 1000})  # should not raise


class TestFindOutputFile:
    def test_finds_exact_file(self, tmp_path):
        expected = tmp_path / "Song.mp3"
        expected.write_text("audio")
        template = str(tmp_path / "Song.%(ext)s")
        result = _find_output_file(None, "Song", "mp3", template)
        assert result == str(expected)

    def test_finds_file_by_extension_scan(self, tmp_path):
        (tmp_path / "Song.flac").write_text("audio")
        template = str(tmp_path / "Song.%(ext)s")
        result = _find_output_file(None, "Song", "flac", template)
        assert result.endswith(".flac")

    def test_returns_expected_path_when_no_file_exists(self, tmp_path):
        template = str(tmp_path / "Song.%(ext)s")
        result = _find_output_file(None, "Song", "mp3", template)
        assert result == str(tmp_path / "Song.mp3")
