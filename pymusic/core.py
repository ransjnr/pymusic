"""High-level PyMusic API — the main entry point for library users."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, List, Optional, Union

from pymusic.config import Config
from pymusic.exceptions import UnsupportedURLError, PyMusicError
from pymusic.models import Playlist, SearchResult, Source, Track
from pymusic.utils import (
    detect_source,
    is_youtube_playlist,
    is_soundcloud_set,
    is_spotify_playlist,
    spotify_entity_type,
)

logger = logging.getLogger(__name__)


class PyMusic:
    """Main interface for downloading music with pyMusic.

    Example::

        pm = PyMusic(output_dir="~/Music", format="mp3", quality=320)
        track = pm.download("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        print(track.title, track.artist)
    """

    def __init__(
        self,
        output_dir: str = None,
        format: str = "mp3",
        quality: int = 192,
        embed_metadata: bool = True,
        embed_thumbnail: bool = True,
        create_subdirs: bool = False,
        overwrite: bool = False,
        verbose: bool = False,
        quiet: bool = False,
        spotify_client_id: Optional[str] = None,
        spotify_client_secret: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        if config is not None:
            self.config = config
        else:
            kwargs = dict(
                format=format,
                quality=quality,
                embed_metadata=embed_metadata,
                embed_thumbnail=embed_thumbnail,
                create_subdirs=create_subdirs,
                overwrite=overwrite,
                verbose=verbose,
                quiet=quiet,
            )
            if output_dir is not None:
                kwargs["output_dir"] = output_dir
            if spotify_client_id is not None:
                kwargs["spotify_client_id"] = spotify_client_id
            if spotify_client_secret is not None:
                kwargs["spotify_client_secret"] = spotify_client_secret
            self.config = Config(**kwargs)

        if not quiet:
            logging.basicConfig(
                level=logging.DEBUG if verbose else logging.INFO,
                format="%(levelname)s: %(message)s",
            )

    # ------------------------------------------------------------------
    # Smart download router
    # ------------------------------------------------------------------

    def download(
        self,
        url: str,
        progress_callback: Optional[Callable] = None,
        item_callback: Optional[Callable] = None,
    ) -> Union[Track, Playlist]:
        """Download a track or playlist from any supported source.

        Automatically detects the source (YouTube, SoundCloud, Spotify, etc.)
        and whether the URL is a single track or a playlist/album.

        Returns a Track for single downloads or a Playlist for collections.
        """
        source = detect_source(url)

        if source == "youtube":
            if is_youtube_playlist(url):
                return self.download_playlist(url, progress_callback, item_callback)
            return self.download_track_url(url, progress_callback)

        if source == "soundcloud":
            if is_soundcloud_set(url):
                return self.download_playlist(url, progress_callback, item_callback)
            return self.download_track_url(url, progress_callback)

        if source == "spotify":
            entity = spotify_entity_type(url)
            if entity in ("album", "playlist"):
                return self.download_playlist(url, progress_callback, item_callback)
            return self.download_track_url(url, progress_callback)

        # Bandcamp, generic, etc.
        return self.download_track_url(url, progress_callback)

    # ------------------------------------------------------------------
    # Single track downloads
    # ------------------------------------------------------------------

    def download_track_url(
        self,
        url: str,
        progress_callback: Optional[Callable] = None,
    ) -> Track:
        """Download a single track from any supported URL."""
        source = detect_source(url)

        if source == "youtube":
            from pymusic import youtube
            return youtube.download_single(url, self.config, progress_callback)

        if source == "soundcloud":
            from pymusic import soundcloud
            return soundcloud.download_track(url, self.config, progress_callback)

        if source == "spotify":
            from pymusic import spotify
            return spotify.download_track(url, self.config, progress_callback)

        # Bandcamp, generic
        from pymusic import generic
        return generic.download_url(url, self.config, progress_callback)

    # ------------------------------------------------------------------
    # Playlist / album downloads
    # ------------------------------------------------------------------

    def download_playlist(
        self,
        url: str,
        progress_callback: Optional[Callable] = None,
        item_callback: Optional[Callable] = None,
    ) -> Playlist:
        """Download a playlist or album from any supported URL."""
        source = detect_source(url)

        if source == "youtube":
            from pymusic import youtube
            return youtube.download_playlist(url, self.config, progress_callback, item_callback)

        if source == "soundcloud":
            from pymusic import soundcloud
            return soundcloud.download_set(url, self.config, progress_callback, item_callback)

        if source == "spotify":
            from pymusic import spotify
            return spotify.download_playlist(url, self.config, progress_callback, item_callback)

        from pymusic import generic
        return generic.download_playlist_url(url, self.config, progress_callback, item_callback)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        source: str = "youtube",
        limit: int = 10,
    ) -> List[SearchResult]:
        """Search for music and return a list of results without downloading.

        Args:
            query: Search query string.
            source: Where to search. One of 'youtube', 'soundcloud'.
            limit: Maximum number of results to return.

        Returns:
            List of SearchResult objects.
        """
        if source == "soundcloud":
            from pymusic import soundcloud
            return soundcloud.search_soundcloud(query, self.config, limit)

        # Default to YouTube
        from pymusic import youtube
        return youtube.search_youtube(query, self.config, limit)

    def search_and_download(
        self,
        query: str,
        source: str = "youtube",
        progress_callback: Optional[Callable] = None,
    ) -> Track:
        """Search and download the best matching track.

        Args:
            query: Search string (e.g. "Never Gonna Give You Up Rick Astley").
            source: Where to search ('youtube' or 'soundcloud').
            progress_callback: Optional progress hook.

        Returns:
            The downloaded Track.
        """
        results = self.search(query, source=source, limit=3)
        if not results:
            from pymusic.exceptions import SearchError
            raise SearchError(query, "No results found")

        track = results[0].to_track()
        from pymusic.downloader import download_track
        download_track(track, self.config, progress_callback)
        return track

    # ------------------------------------------------------------------
    # Metadata / info (no download)
    # ------------------------------------------------------------------

    def get_info(self, url: str) -> Union[Track, Playlist]:
        """Fetch metadata for a URL without downloading anything."""
        source = detect_source(url)

        if source == "youtube":
            from pymusic import youtube
            if is_youtube_playlist(url):
                return youtube.get_playlist_info(url, self.config)
            return youtube.get_track_info(url, self.config)

        if source == "soundcloud":
            from pymusic import soundcloud
            if is_soundcloud_set(url):
                return soundcloud.get_set_info(url, self.config)
            return soundcloud.get_track_info(url, self.config)

        if source == "spotify":
            from pymusic import spotify
            entity = spotify_entity_type(url)
            if entity == "album":
                return spotify.get_album_info(url, self.config)
            if entity == "playlist":
                return spotify.get_playlist_info(url, self.config)
            return spotify.get_track_info(url, self.config)

        from pymusic import generic
        info = generic.get_info(url, self.config)
        from pymusic.generic import _info_to_track
        return _info_to_track(info)

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def output_dir(self) -> Path:
        return self.config.output_path

    def set_output_dir(self, path: str) -> None:
        self.config.output_dir = path

    def set_format(self, fmt: str) -> None:
        from pymusic.models import AudioFormat
        AudioFormat.from_string(fmt)  # Validate
        self.config.format = fmt

    def set_quality(self, quality: int) -> None:
        self.config.quality = quality
