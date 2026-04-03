"""Core yt-dlp based downloader used by all source modules."""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yt_dlp

from pymusic.config import Config
from pymusic.exceptions import DownloadError
from pymusic.models import Track, DownloadStatus
from pymusic.utils import build_output_path, sanitize_filename, ensure_dir

logger = logging.getLogger(__name__)


class ProgressHook:
    """Translate yt-dlp progress hooks into a cleaner interface."""

    def __init__(self, track: Track, callback: Optional[Callable] = None):
        self.track = track
        self.callback = callback

    def __call__(self, d: dict):
        status = d.get("status")
        if status == "downloading":
            self.track.status = DownloadStatus.DOWNLOADING
            if self.callback:
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                speed = d.get("speed", 0)
                self.callback(self.track, downloaded, total, speed)
        elif status == "finished":
            self.track.status = DownloadStatus.PROCESSING
        elif status == "error":
            self.track.status = DownloadStatus.FAILED


def build_ydl_opts(
    config: Config,
    output_template: str,
    progress_hooks: Optional[List[Callable]] = None,
    extra_opts: Optional[Dict[str, Any]] = None,
) -> dict:
    """Build the yt-dlp options dictionary."""
    opts = {
        "quiet": config.quiet,
        "verbose": config.verbose,
        "no_warnings": config.quiet,
        "outtmpl": output_template,
        "writethumbnail": config.embed_thumbnail,
        "writeinfojson": False,
        "noplaylist": False,
        "ignoreerrors": False,
        "retries": config.retries,
        "socket_timeout": config.socket_timeout,
        "progress_hooks": progress_hooks or [],
    }

    # Format / postprocessors
    opts.update(config.ydl_format_opts())

    # Metadata embedding
    if config.embed_metadata:
        pp_list = opts.get("postprocessors", [])
        pp_list.append({"key": "FFmpegMetadata", "add_metadata": True})
        if config.embed_thumbnail:
            pp_list.append({"key": "EmbedThumbnail"})
        opts["postprocessors"] = pp_list

    # Optional rate limiting
    if config.rate_limit:
        opts["ratelimit"] = config.rate_limit

    # Proxy
    if config.proxy:
        opts["proxy"] = config.proxy

    # Cookies
    if config.cookies_file:
        opts["cookiefile"] = config.cookies_file

    # Overwrite protection
    opts["nooverwrites"] = not config.overwrite

    # Merge extra options
    if extra_opts:
        opts.update(extra_opts)

    return opts


def extract_info(url: str, ydl_opts: dict) -> dict:
    """Run yt-dlp info extraction without downloading."""
    extract_opts = {**ydl_opts, "skip_download": True, "quiet": True}
    with yt_dlp.YoutubeDL(extract_opts) as ydl:
        try:
            return ydl.extract_info(url, download=False) or {}
        except yt_dlp.utils.DownloadError as exc:
            raise DownloadError(str(exc), url=url, cause=exc) from exc


def download_track(
    track: Track,
    config: Config,
    progress_callback: Optional[Callable] = None,
) -> str:
    """Download a single track using yt-dlp. Returns the output file path."""
    out_dir = config.output_path
    ensure_dir(out_dir)

    # Build per-track output template
    safe_title = sanitize_filename(track.title or "%(title)s")
    safe_artist = sanitize_filename(track.artist or "")

    if config.create_subdirs and safe_artist:
        sub = out_dir / safe_artist
        if track.album:
            sub = sub / sanitize_filename(track.album)
        ensure_dir(sub)
        template = str(sub / f"{safe_title}.%(ext)s")
    else:
        template = str(out_dir / f"{safe_title}.%(ext)s")

    hook = ProgressHook(track, progress_callback)
    opts = build_ydl_opts(config, template, progress_hooks=[hook])

    track.status = DownloadStatus.DOWNLOADING
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([track.url])
    except yt_dlp.utils.DownloadError as exc:
        track.status = DownloadStatus.FAILED
        track.error = str(exc)
        raise DownloadError(str(exc), url=track.url, cause=exc) from exc

    # Resolve the actual file path (extension may change after conversion)
    resolved = _find_output_file(out_dir if not (config.create_subdirs and safe_artist) else None,
                                 safe_title, config.format, template)
    track.file_path = resolved
    track.status = DownloadStatus.COMPLETED
    return resolved


def _find_output_file(directory: Optional[Path], base_name: str, fmt: str, template: str) -> str:
    """Find the downloaded file by scanning near the template path."""
    expected = template.replace("%(ext)s", fmt)
    if os.path.exists(expected):
        return expected

    # Search in the template's directory
    tmpl_dir = Path(template).parent
    candidates = list(tmpl_dir.glob(f"{base_name}.*"))
    if candidates:
        # Prefer matching format
        for c in candidates:
            if c.suffix.lstrip(".") == fmt:
                return str(c)
        return str(candidates[0])

    return expected
