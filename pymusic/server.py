"""Local HTTP companion server for the pyMusic browser extension.

Start with:
    pymusic server
or:
    python -m pymusic.server

Listens on http://127.0.0.1:6173
"""
from __future__ import annotations

import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pymusic import PyMusic, __version__
from pymusic.config import Config
from pymusic.downloader import download_track as _download_track
from pymusic.exceptions import PyMusicError

PORT = 6173
_executor = ThreadPoolExecutor(max_workers=4)

app = FastAPI(title="pyMusic", version=__version__, docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory state ──────────────────────────────────────────────────────────

_jobs: Dict[str, Dict[str, Any]] = {}
_recent: List[Dict[str, Any]] = []


# ── Request models ────────────────────────────────────────────────────────────

class DownloadRequest(BaseModel):
    url: str
    format: str = "mp3"
    quality: int = 192
    output_dir: Optional[str] = None
    embed_metadata: bool = True
    embed_thumbnail: bool = True
    subdirs: bool = False

class SearchRequest(BaseModel):
    query: str
    source: str = "youtube"
    limit: int = 10


# ── Helper ────────────────────────────────────────────────────────────────────

def _track_to_dict(track) -> dict:
    return {
        "title": getattr(track, "title", None),
        "artist": getattr(track, "artist", None),
        "album": getattr(track, "album", None),
        "year": getattr(track, "year", None),
        "duration": getattr(track, "duration", None),
        "duration_str": getattr(track, "duration_str", None),
        "thumbnail_url": getattr(track, "thumbnail_url", None),
        "url": getattr(track, "url", None),
        "source": getattr(getattr(track, "source", None), "value", None),
    }

def _playlist_to_dict(pl) -> dict:
    return {
        "title": pl.title,
        "uploader": pl.uploader,
        "total_tracks": pl.total_tracks,
        "duration_str": pl.duration_str,
        "url": pl.url,
        "source": pl.source.value if pl.source else None,
        "tracks": [_track_to_dict(t) for t in pl.tracks[:50]],
    }


# ── Background download ───────────────────────────────────────────────────────

def _run_download(job_id: str, req: DownloadRequest) -> None:
    job = _jobs[job_id]

    config = Config(
        format=req.format,
        quality=req.quality,
        embed_metadata=req.embed_metadata,
        embed_thumbnail=req.embed_thumbnail,
        create_subdirs=req.subdirs,
        quiet=True,
        **({"output_dir": req.output_dir} if req.output_dir else {}),
    )

    def progress_cb(track, downloaded, total, speed):
        if total:
            job["progress"] = round(downloaded / total * 100, 1)
        job["speed"] = int(speed or 0)
        job["downloaded_bytes"] = downloaded
        job["total_bytes"] = total
        if track.title:
            job["title"] = track.title
        if track.artist:
            job["artist"] = track.artist
        if track.thumbnail_url:
            job["thumbnail"] = track.thumbnail_url

    job["status"] = "downloading"
    try:
        pm = PyMusic(config=config)
        result = pm.download(req.url, progress_callback=progress_cb)

        if hasattr(result, "file_path"):
            job.update({
                "title": result.title,
                "artist": result.artist,
                "thumbnail": getattr(result, "thumbnail_url", None),
                "file_path": result.file_path,
            })
        elif hasattr(result, "tracks"):  # Playlist
            job.update({
                "title": result.title,
                "total_tracks": result.total_tracks,
                "downloaded_count": len(result.downloaded_tracks),
                "failed_count": len(result.failed_tracks),
            })

        job["status"] = "completed"
        job["progress"] = 100
        job["finished_at"] = datetime.now().isoformat()

        _recent.append(dict(job))
        if len(_recent) > 50:
            _recent.pop(0)

    except PyMusicError as exc:
        job["status"] = "failed"
        job["error"] = str(exc)
        job["finished_at"] = datetime.now().isoformat()
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = f"Unexpected error: {exc}"
        job["finished_at"] = datetime.now().isoformat()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__, "port": PORT}


@app.get("/info")
async def get_info(url: str):
    config = Config(quiet=True)
    pm = PyMusic(config=config)
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(_executor, pm.get_info, url)
    except PyMusicError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if hasattr(result, "tracks"):
        return {"type": "playlist", **_playlist_to_dict(result)}
    return {"type": "track", **_track_to_dict(result)}


@app.post("/download")
async def start_download(req: DownloadRequest):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "id": job_id,
        "url": req.url,
        "format": req.format,
        "quality": req.quality,
        "status": "pending",
        "progress": 0,
        "speed": 0,
        "downloaded_bytes": 0,
        "total_bytes": 0,
        "title": None,
        "artist": None,
        "thumbnail": None,
        "file_path": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "finished_at": None,
    }
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_download, job_id, req)
    return {"job_id": job_id}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/events/{job_id}")
async def stream_events(job_id: str):
    """Server-Sent Events stream — polls job state and pushes updates."""
    async def generate():
        seen_state: Optional[str] = None
        deadline = 600  # 10 min timeout
        elapsed = 0.0

        while elapsed < deadline:
            job = _jobs.get(job_id)
            if job is None:
                yield f"data: {json.dumps({'error': 'job not found'})}\n\n"
                return

            snapshot = json.dumps(job, default=str)
            if snapshot != seen_state:
                yield f"data: {snapshot}\n\n"
                seen_state = snapshot

            if job["status"] in ("completed", "failed"):
                yield "data: {\"done\": true}\n\n"
                return

            await asyncio.sleep(0.25)
            elapsed += 0.25

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/search")
async def search(req: SearchRequest):
    config = Config(quiet=True)
    pm = PyMusic(config=config)
    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(
            _executor, lambda: pm.search(req.query, source=req.source, limit=req.limit)
        )
    except PyMusicError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "results": [
            {
                "title": r.title,
                "artist": r.artist,
                "duration": r.duration,
                "duration_str": r.duration_str,
                "url": r.url,
                "thumbnail_url": getattr(r, "thumbnail_url", None),
                "display_name": r.display_name,
            }
            for r in results
        ]
    }


@app.get("/recent")
async def get_recent():
    return {"downloads": list(reversed(_recent[-20:]))}


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    if job_id in _jobs:
        del _jobs[job_id]
        return {"cancelled": True}
    raise HTTPException(status_code=404, detail="Job not found")


# ── Entry point ───────────────────────────────────────────────────────────────

def start(host: str = "127.0.0.1", port: int = PORT, open_browser: bool = False):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    start()
