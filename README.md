# pyMusic Downloader

[![PyPI version](https://badge.fury.io/py/pymusic-downloader.svg)](https://pypi.org/project/pymusic-downloader/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Python library and CLI tool to download music from YouTube, SoundCloud, Spotify, Bandcamp, and more.

## Features

- **YouTube**: Download single tracks or entire playlists
- **SoundCloud**: Download tracks and playlists
- **Spotify**: Resolve Spotify metadata and download via YouTube
- **Bandcamp**: Download tracks and albums
- **Generic**: Download from any yt-dlp supported source
- **Formats**: MP3, M4A, FLAC, WAV, OGG
- **Metadata**: Automatic ID3 tag embedding (title, artist, album, artwork)
- **CLI**: Full-featured command-line interface
- **Python API**: Clean, intuitive programmatic interface

## Installation

```bash
pip install pymusic-downloader
```

> **Note:** `ffmpeg` must be installed on your system for audio conversion.
> - macOS: `brew install ffmpeg`
> - Ubuntu/Debian: `sudo apt install ffmpeg`
> - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

Install from source:

```bash
git clone https://github.com/ransjnr/pymusic
cd pymusic
pip install -e .
```

## Quick Start

### CLI Usage

```bash
# Download a YouTube video as MP3
pymusic download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Download a YouTube playlist
pymusic download "https://www.youtube.com/playlist?list=PLxxxxxx"

# Download from SoundCloud
pymusic download "https://soundcloud.com/artist/track"

# Download a Spotify track (resolves via YouTube)
pymusic download "https://open.spotify.com/track/xxxxxx" \
  --spotify-id YOUR_CLIENT_ID --spotify-secret YOUR_CLIENT_SECRET

# Specify output format and directory
pymusic download "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --format mp3 --quality 320 --output ~/Music

# Search and download
pymusic search "Never Gonna Give You Up Rick Astley" --download

# Browse results and pick interactively
pymusic search "Daft Punk" --pick

# Show metadata without downloading
pymusic info "https://www.youtube.com/playlist?list=PLxxxxxx"
```

### Python API Usage

```python
from pymusic import PyMusic

# Initialize
pm = PyMusic(output_dir="~/Music", format="mp3", quality=320)

# Download a single YouTube track
track = pm.download("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(f"Downloaded: {track.title} by {track.artist}")
print(f"Saved to:   {track.file_path}")

# Download a YouTube playlist
playlist = pm.download("https://www.youtube.com/playlist?list=PLxxxxxx")
print(f"{playlist.title}: {len(playlist.downloaded_tracks)}/{playlist.total_tracks} tracks")

# Search YouTube and download
results = pm.search("Never Gonna Give You Up", limit=5)
for i, r in enumerate(results, 1):
    print(f"{i}. {r.display_name} [{r.duration_str}]")

track = pm.search_and_download("Never Gonna Give You Up Rick Astley")

# Download from SoundCloud
track = pm.download("https://soundcloud.com/artist/track")

# Download from Spotify (resolves via YouTube)
pm2 = PyMusic(
    spotify_client_id="your_id",
    spotify_client_secret="your_secret",
)
track = pm2.download("https://open.spotify.com/track/xxxxxx")

# Get metadata without downloading
info = pm.get_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(f"{info.title} — {info.duration_str}")
```

### Advanced Configuration

```python
from pymusic import PyMusic
from pymusic.config import Config

config = Config(
    output_dir="~/Music",
    format="mp3",
    quality=320,
    embed_metadata=True,
    embed_thumbnail=True,
    create_subdirs=True,        # Organise as Artist/Album/Track
    overwrite=False,
    playlist_start=1,
    playlist_end=50,
    rate_limit="1M",            # Limit download speed
    proxy="socks5://127.0.0.1:1080",
    spotify_client_id="your_id",
    spotify_client_secret="your_secret",
)

pm = PyMusic(config=config)
```

### Environment Variables

```bash
export SPOTIFY_CLIENT_ID=your_spotify_client_id
export SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
export PYMUSIC_OUTPUT_DIR=~/Music
export PYMUSIC_FORMAT=mp3
export PYMUSIC_QUALITY=320
```

## Supported Sources

| Source     | Singles | Playlists | Metadata | Artwork |
|------------|:-------:|:---------:|:--------:|:-------:|
| YouTube    | ✅      | ✅        | ✅       | ✅      |
| SoundCloud | ✅      | ✅        | ✅       | ✅      |
| Spotify*   | ✅      | ✅        | ✅       | ✅      |
| Bandcamp   | ✅      | ✅        | ✅       | ✅      |
| Generic    | ✅      | ✅        | ✅       | ✅      |

\* Spotify audio is sourced from YouTube — only metadata comes from Spotify.

## Audio Formats

| Format | Quality Options          |
|--------|--------------------------|
| MP3    | 64, 96, 128, 192, 256, 320 kbps |
| M4A    | Best available           |
| FLAC   | Lossless                 |
| WAV    | Lossless                 |
| OGG    | Variable bitrate         |

## CLI Reference

```
Usage: pymusic [OPTIONS] COMMAND [ARGS]...

Commands:
  download  Download a track or playlist from URL
  search    Search for music and optionally download
  info      Show metadata for a URL without downloading

Options:
  -V, --version  Show version and exit
  --help         Show help message and exit
```

### `pymusic download` options

| Flag | Default | Description |
|------|---------|-------------|
| `-o, --output` | `~/Music` | Output directory |
| `-f, --format` | `mp3` | Audio format (mp3/m4a/flac/wav/ogg) |
| `-q, --quality` | `192` | Bitrate in kbps (MP3 only) |
| `--start` | `1` | Playlist start index |
| `--end` | — | Playlist end index |
| `--reverse` | `false` | Download playlist in reverse |
| `--shuffle` | `false` | Download playlist shuffled |
| `--subdirs` | `false` | Create Artist/Album subdirectories |
| `--overwrite` | `false` | Overwrite existing files |
| `--rate-limit` | — | Speed limit (e.g. `500K`, `1M`) |
| `--proxy` | — | HTTP/SOCKS proxy URL |
| `--cookies` | — | Path to Netscape cookies file |
| `-v, --verbose` | `false` | Verbose output |
| `--quiet` | `false` | Suppress all output |

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please open an issue or pull request on [GitHub](https://github.com/ransjnr/pymusic).
