# pyMusic

A powerful Python library and CLI tool to download music from YouTube, SoundCloud, Spotify, Bandcamp, and more.

## Features

- **YouTube**: Download single tracks or entire playlists
- **SoundCloud**: Download tracks and playlists
- **Spotify**: Resolve Spotify metadata and download via YouTube
- **Generic**: Download from any yt-dlp supported source
- **Formats**: MP3, M4A, FLAC, WAV, OGG
- **Metadata**: Automatic ID3 tag embedding (title, artist, album, artwork)
- **CLI**: Full-featured command-line interface
- **Python API**: Clean, intuitive programmatic interface

## Installation

```bash
pip install pymusic
```

Or install from source:

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
pymusic download "https://open.spotify.com/track/xxxxxx"

# Specify output format and directory
pymusic download "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --format mp3 --output ~/Music

# Search and download
pymusic search "Never Gonna Give You Up Rick Astley"

# Download with quality setting
pymusic download "URL" --quality 320

# Show progress and verbose info
pymusic download "URL" --verbose
```

### Python API Usage

```python
from pymusic import PyMusic

# Initialize
pm = PyMusic(output_dir="~/Music", format="mp3", quality=320)

# Download a single YouTube track
track = pm.download("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(f"Downloaded: {track.title} by {track.artist}")

# Download a YouTube playlist
playlist = pm.download_playlist("https://www.youtube.com/playlist?list=PLxxxxxx")
for track in playlist.tracks:
    print(f"  - {track.title}")

# Search YouTube and download
results = pm.search("Never Gonna Give You Up", limit=5)
pm.download_track(results[0])

# Download from SoundCloud
track = pm.download("https://soundcloud.com/artist/track")

# Download from Spotify (resolves metadata then downloads via YouTube)
track = pm.download("https://open.spotify.com/track/xxxxxx")
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
    create_subdirs=True,       # Organise as Artist/Album/Track
    spotify_client_id="your_id",
    spotify_client_secret="your_secret",
)

pm = PyMusic(config=config)
```

## Supported Sources

| Source     | Singles | Playlists | Metadata | Artwork |
|------------|---------|-----------|----------|---------|
| YouTube    | ✅      | ✅        | ✅       | ✅      |
| SoundCloud | ✅      | ✅        | ✅       | ✅      |
| Spotify    | ✅*     | ✅*       | ✅       | ✅      |
| Bandcamp   | ✅      | ✅        | ✅       | ✅      |
| Generic    | ✅      | ✅        | ✅       | ✅      |

\* Spotify playback is resolved through YouTube search.

## Audio Formats

| Format | Quality Options       |
|--------|-----------------------|
| MP3    | 128, 192, 256, 320 kbps |
| M4A    | Best available        |
| FLAC   | Lossless              |
| WAV    | Lossless              |
| OGG    | Variable bitrate      |

## Environment Variables

```bash
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
PYMUSIC_OUTPUT_DIR=~/Music
PYMUSIC_FORMAT=mp3
PYMUSIC_QUALITY=320
```

## License

MIT License - see [LICENSE](LICENSE) for details.
