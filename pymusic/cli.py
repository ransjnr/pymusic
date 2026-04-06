"""Command-line interface for pyMusic."""
from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
from typing import Optional

import click
from colorama import Fore, Style, init as colorama_init

from pymusic import PyMusic, __version__
from pymusic.config import Config
from pymusic.exceptions import PyMusicError, SpotifyAuthError
from pymusic.models import Track, Playlist, DownloadStatus
from pymusic.utils import format_duration, format_size

colorama_init(autoreset=True)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared options
# ---------------------------------------------------------------------------

_COMMON_OPTIONS = [
    click.option(
        "-o", "--output", "output_dir",
        default=None,
        envvar="PYMUSIC_OUTPUT_DIR",
        show_default=True,
        help="Output directory (default: ~/Music).",
    ),
    click.option(
        "-f", "--format",
        default="mp3",
        type=click.Choice(["mp3", "m4a", "flac", "wav", "ogg"], case_sensitive=False),
        envvar="PYMUSIC_FORMAT",
        show_default=True,
        help="Audio format.",
    ),
    click.option(
        "-q", "--quality",
        default=192,
        type=click.Choice(["64", "96", "128", "192", "256", "320"], case_sensitive=False),
        envvar="PYMUSIC_QUALITY",
        show_default=True,
        help="Audio bitrate in kbps (MP3 only).",
    ),
    click.option("--no-metadata", is_flag=True, default=False, help="Skip embedding metadata tags."),
    click.option("--no-thumbnail", is_flag=True, default=False, help="Skip embedding album art."),
    click.option("--subdirs", is_flag=True, default=False, help="Create Artist/Album subdirectories."),
    click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing files."),
    click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose output."),
    click.option("--quiet", is_flag=True, default=False, help="Suppress all output."),
    click.option(
        "--proxy",
        default=None,
        help="HTTP/SOCKS proxy (e.g. socks5://127.0.0.1:1080).",
    ),
    click.option("--cookies", default=None, help="Path to Netscape cookies file."),
    click.option(
        "--spotify-id",
        envvar="SPOTIFY_CLIENT_ID",
        default=None,
        help="Spotify API client ID.",
    ),
    click.option(
        "--spotify-secret",
        envvar="SPOTIFY_CLIENT_SECRET",
        default=None,
        help="Spotify API client secret.",
    ),
]


def add_common_options(fn):
    """Decorator that adds all common options to a click command."""
    for option in reversed(_COMMON_OPTIONS):
        fn = option(fn)
    return fn


def build_config(
    output_dir, format, quality, no_metadata, no_thumbnail, subdirs,
    overwrite, verbose, quiet, proxy, cookies, spotify_id, spotify_secret,
    **_extra,
) -> Config:
    kwargs = dict(
        format=format,
        quality=int(quality),
        embed_metadata=not no_metadata,
        embed_thumbnail=not no_thumbnail,
        create_subdirs=subdirs,
        overwrite=overwrite,
        verbose=verbose,
        quiet=quiet,
    )
    if output_dir:
        kwargs["output_dir"] = output_dir
    if proxy:
        kwargs["proxy"] = proxy
    if cookies:
        kwargs["cookies_file"] = cookies
    if spotify_id:
        kwargs["spotify_client_id"] = spotify_id
    if spotify_secret:
        kwargs["spotify_client_secret"] = spotify_secret
    return Config(**kwargs)


# ---------------------------------------------------------------------------
# Progress display
# ---------------------------------------------------------------------------

class ProgressPrinter:
    def __init__(self, quiet: bool = False):
        self.quiet = quiet
        self._last_pct = -1

    def progress_callback(self, track: Track, downloaded: int, total: int, speed: float):
        if self.quiet or not total:
            return
        pct = int(downloaded / total * 100)
        if pct == self._last_pct:
            return
        self._last_pct = pct
        bar_len = 30
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        speed_str = format_size(int(speed or 0)) + "/s" if speed else ""
        click.echo(
            f"\r  [{bar}] {pct:3d}%  {format_size(downloaded)}/{format_size(total)}  {speed_str}   ",
            nl=False,
        )
        sys.stdout.flush()

    def done(self):
        if not self.quiet:
            click.echo()

    def item_callback(self, track: Track, index: int, total: int):
        if self.quiet:
            return
        self._last_pct = -1
        status_icon = (
            Fore.GREEN + "✓" if track.status == DownloadStatus.COMPLETED
            else Fore.RED + "✗"
        )
        click.echo(
            f"\n{status_icon}{Style.RESET_ALL} [{index}/{total}] "
            f"{Fore.CYAN}{track.display_name}{Style.RESET_ALL}"
        )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(__version__, "-V", "--version")
def main():
    """pyMusic — Download music from YouTube, SoundCloud, Spotify, and more."""


@main.command("download")
@click.argument("url")
@add_common_options
@click.option(
    "--start", default=1, type=int, show_default=True,
    help="Playlist start index (1-based).",
)
@click.option(
    "--end", default=None, type=int,
    help="Playlist end index (inclusive, 1-based).",
)
@click.option("--reverse", is_flag=True, default=False, help="Download playlist in reverse order.")
@click.option("--shuffle", is_flag=True, default=False, help="Download playlist in random order.")
@click.option("--rate-limit", default=None, help="Download speed limit (e.g. 500K, 1M).")
def download_cmd(url, start, end, reverse, shuffle, rate_limit, **kwargs):
    """Download a track or playlist from URL.

    Supports YouTube, SoundCloud, Spotify (requires credentials), Bandcamp,
    and any other yt-dlp compatible source.

    \b
    Examples:
      pymusic download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
      pymusic download "https://www.youtube.com/playlist?list=PLxxx" --format flac
      pymusic download "https://soundcloud.com/artist/track" -o ~/Downloads
      pymusic download "https://open.spotify.com/track/xxx" --spotify-id ID --spotify-secret SECRET
    """
    config = build_config(**kwargs)
    config.playlist_start = start
    config.playlist_end = end
    config.playlist_reverse = reverse
    config.playlist_random = shuffle
    if rate_limit:
        config.rate_limit = rate_limit

    quiet = kwargs.get("quiet", False)
    verbose = kwargs.get("verbose", False)

    if not quiet:
        click.echo(f"\n{Fore.CYAN}pyMusic{Style.RESET_ALL} — {url}")
        click.echo(f"  Format: {config.format.upper()}  Quality: {config.quality} kbps  Output: {config.output_path}\n")

    printer = ProgressPrinter(quiet=quiet)
    pm = PyMusic(config=config)

    try:
        result = pm.download(
            url,
            progress_callback=printer.progress_callback,
            item_callback=printer.item_callback,
        )
    except SpotifyAuthError as exc:
        click.echo(f"\n{Fore.RED}Spotify auth error:{Style.RESET_ALL} {exc}", err=True)
        click.echo(
            "  Set --spotify-id and --spotify-secret or use environment variables "
            "SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET.",
            err=True,
        )
        sys.exit(1)
    except PyMusicError as exc:
        click.echo(f"\n{Fore.RED}Error:{Style.RESET_ALL} {exc}", err=True)
        sys.exit(1)

    printer.done()

    if isinstance(result, Track):
        _print_track_result(result, quiet)
    elif isinstance(result, Playlist):
        _print_playlist_result(result, quiet)


@main.command("search")
@click.argument("query")
@add_common_options
@click.option(
    "-n", "--limit", default=10, type=int, show_default=True,
    help="Number of results to show.",
)
@click.option(
    "-s", "--source",
    default="youtube",
    type=click.Choice(["youtube", "soundcloud"], case_sensitive=False),
    show_default=True,
    help="Where to search.",
)
@click.option(
    "--download", "-d", is_flag=True, default=False,
    help="Download the first result immediately.",
)
@click.option(
    "--pick", is_flag=True, default=False,
    help="Interactively pick a result to download.",
)
def search_cmd(query, limit, source, download, pick, **kwargs):
    """Search for music and optionally download.

    \b
    Examples:
      pymusic search "Never Gonna Give You Up"
      pymusic search "Daft Punk" --source soundcloud -n 5
      pymusic search "Rick Astley" --download
      pymusic search "Bohemian Rhapsody" --pick
    """
    config = build_config(**kwargs)
    quiet = kwargs.get("quiet", False)
    pm = PyMusic(config=config)

    if not quiet:
        click.echo(f"\n{Fore.CYAN}Searching {source} for:{Style.RESET_ALL} {query!r}\n")

    try:
        results = pm.search(query, source=source, limit=limit)
    except PyMusicError as exc:
        click.echo(f"{Fore.RED}Search error:{Style.RESET_ALL} {exc}", err=True)
        sys.exit(1)

    if not results:
        click.echo("No results found.")
        return

    for i, result in enumerate(results, start=1):
        dur = f"  [{result.duration_str}]" if result.duration else ""
        artist = f" — {result.artist}" if result.artist else ""
        click.echo(
            f"  {Fore.YELLOW}{i:2d}.{Style.RESET_ALL} "
            f"{Fore.CYAN}{result.title}{Style.RESET_ALL}"
            f"{artist}{Fore.WHITE}{dur}{Style.RESET_ALL}"
        )
        if not quiet:
            click.echo(f"      {result.url}")

    if pick and not quiet:
        choices = [str(i) for i in range(1, len(results) + 1)]
        idx_str = click.prompt(
            "\nEnter number to download",
            type=click.Choice(choices),
            show_choices=False,
        )
        selected = results[int(idx_str) - 1]
        click.echo(f"\nDownloading: {selected.display_name}")
        printer = ProgressPrinter(quiet=quiet)
        track = selected.to_track()
        from pymusic.downloader import download_track
        try:
            download_track(track, config, printer.progress_callback)
        except PyMusicError as exc:
            click.echo(f"\n{Fore.RED}Error:{Style.RESET_ALL} {exc}", err=True)
            sys.exit(1)
        printer.done()
        _print_track_result(track, quiet)
        return

    if download:
        best = results[0]
        if not quiet:
            click.echo(f"\nDownloading top result: {best.display_name}")
        printer = ProgressPrinter(quiet=quiet)
        track = best.to_track()
        from pymusic.downloader import download_track
        try:
            download_track(track, config, printer.progress_callback)
        except PyMusicError as exc:
            click.echo(f"\n{Fore.RED}Error:{Style.RESET_ALL} {exc}", err=True)
            sys.exit(1)
        printer.done()
        _print_track_result(track, quiet)


@main.command("info")
@click.argument("url")
@click.option("--spotify-id", envvar="SPOTIFY_CLIENT_ID", default=None, help="Spotify client ID.")
@click.option("--spotify-secret", envvar="SPOTIFY_CLIENT_SECRET", default=None, help="Spotify client secret.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show extra fields.")
def info_cmd(url, spotify_id, spotify_secret, verbose):
    """Show metadata for a URL without downloading.

    \b
    Examples:
      pymusic info "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
      pymusic info "https://www.youtube.com/playlist?list=PLxxx"
    """
    config = Config(
        spotify_client_id=spotify_id,
        spotify_client_secret=spotify_secret,
        verbose=verbose,
        quiet=True,
    )
    pm = PyMusic(config=config)

    try:
        result = pm.get_info(url)
    except PyMusicError as exc:
        click.echo(f"{Fore.RED}Error:{Style.RESET_ALL} {exc}", err=True)
        sys.exit(1)

    if isinstance(result, Track):
        click.echo(f"\n{Fore.CYAN}Track Info{Style.RESET_ALL}")
        click.echo(f"  Title:    {result.title}")
        click.echo(f"  Artist:   {result.artist}")
        click.echo(f"  Album:    {result.album}")
        click.echo(f"  Year:     {result.year}")
        click.echo(f"  Duration: {result.duration_str}")
        click.echo(f"  Source:   {result.source.value}")
        click.echo(f"  URL:      {result.url}")
    elif isinstance(result, Playlist):
        click.echo(f"\n{Fore.CYAN}Playlist Info{Style.RESET_ALL}")
        click.echo(f"  Title:    {result.title}")
        click.echo(f"  Uploader: {result.uploader}")
        click.echo(f"  Tracks:   {result.total_tracks}")
        click.echo(f"  Duration: {result.duration_str}")
        click.echo(f"  Source:   {result.source.value}")
        if verbose:
            click.echo(f"\n  {'#':>3}  {'Title':<50}  {'Duration':>8}")
            click.echo("  " + "-" * 65)
            for t in result.tracks:
                click.echo(f"  {t.track_number:>3}  {t.title[:50]:<50}  {t.duration_str:>8}")


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _print_track_result(track: Track, quiet: bool):
    if quiet:
        if track.file_path:
            click.echo(track.file_path)
        return

    if track.status == DownloadStatus.COMPLETED:
        click.echo(f"\n{Fore.GREEN}Downloaded:{Style.RESET_ALL} {track.display_name}")
        if track.file_path:
            click.echo(f"  Saved to: {track.file_path}")
    else:
        click.echo(f"\n{Fore.RED}Failed:{Style.RESET_ALL} {track.error or 'Unknown error'}", err=True)


def _print_playlist_result(playlist: Playlist, quiet: bool):
    if quiet:
        for t in playlist.downloaded_tracks:
            click.echo(t.file_path)
        return

    downloaded = len(playlist.downloaded_tracks)
    failed = len(playlist.failed_tracks)
    total = playlist.total_tracks

    click.echo(f"\n{Fore.CYAN}Playlist:{Style.RESET_ALL} {playlist.title}")
    click.echo(
        f"  {Fore.GREEN}{downloaded} downloaded{Style.RESET_ALL}  "
        f"{Fore.RED}{failed} failed{Style.RESET_ALL}  "
        f"/ {total} total"
    )
    if playlist.failed_tracks:
        click.echo(f"\n{Fore.RED}Failed tracks:{Style.RESET_ALL}")
        for t in playlist.failed_tracks:
            click.echo(f"  - {t.display_name}: {t.error}")


@main.command("server")
@click.option(
    "--host", default="127.0.0.1", show_default=True,
    help="Host to bind the server to.",
)
@click.option(
    "--port", default=6173, show_default=True, type=int,
    help="Port to listen on.",
)
def server_cmd(host, port):
    """Start the local companion server for the browser extension.

    The extension connects to http://127.0.0.1:6173 to download music
    directly from your browser.

    \b
    Usage:
      pymusic server
      pymusic server --port 6173
    """
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        click.echo(
            f"{Fore.RED}Error:{Style.RESET_ALL} Server dependencies not installed.\n"
            "  Run: pip install 'pymusic-downloader[server]'",
            err=True,
        )
        sys.exit(1)

    from pymusic.server import app, PORT

    click.echo(
        f"\n{Fore.CYAN}pyMusic Server{Style.RESET_ALL} v{__version__}\n"
        f"  Listening on {Fore.GREEN}http://{host}:{port}{Style.RESET_ALL}\n"
        f"  Load the browser extension and start downloading!\n"
        f"  Press {Fore.YELLOW}Ctrl+C{Style.RESET_ALL} to stop.\n"
    )

    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
