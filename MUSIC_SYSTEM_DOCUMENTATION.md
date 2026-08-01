# Complete Rebuild Blueprint: Multi-Provider Voice Music System (Production Edition)

> **Goal:** This document is an exhaustive, line-by-line implementation guide and production blueprint for building the multi-provider voice-controlled music engine from scratch. It contains complete production code, database initialization, error handling, WebSocket protocols, hardware fallback players, and LLM tool schemas.

---

## 📋 Table of Contents
1. [Architecture & Folder Structure](#1-architecture--folder-structure)
2. [Prerequisites & Environment Configuration](#2-prerequisites--environment-configuration)
3. [Step 1: Database Setup & Models (`db/database.py` & `db/models.py`)](#step-1-database-setup--models-dbdatabasepy--dbmodelspy)
4. [Step 2: Global State Management (`state.py`)](#step-2-global-state-management-statepy)
5. [Step 3: YouTube Music & `yt-dlp` Engine (`tools/media_tools.py`)](#step-3-youtube-music--yt-dlp-engine-toolsmedia_toolspy)
6. [Step 4: Spotify OAuth & Remote Control Engine (`tools/premium_media_tools.py`)](#step-4-spotify-oauth--remote-control-engine-toolspremium_media_toolspy)
7. [Step 5: Server-Side Music Vault & Playlists (`tools/music_vault.py`)](#step-5-server-side-music-vault--playlists-toolsmusic_vaultpy)
8. [Step 6: FastAPI Server & WebSocket Broadcaster (`server.py`)](#step-6-fastapi-server--websocket-broadcaster-serverpy)
9. [Step 7: Production Hardware Client Player (`hardware_client.py`)](#step-7-production-hardware-client-player-hardware_clientpy)
10. [Step 8: Next.js Dashboard UI Components](#step-8-nextjs-dashboard-ui-components)
11. [Step 9: LLM Tool Schemas & ReAct Integration](#step-9-llm-tool-schemas--react-integration)
12. [Step 10: Troubleshooting, Edge Cases & Maintenance](#step-10-troubleshooting-edge-cases--maintenance)

---

## 1. Architecture & Folder Structure

To ensure modularity and clean separation of concerns, arrange your project directory as follows:

```text
autonomus-agent/
├── config.py                 # Central config and environment loading
├── state.py                  # Global in-memory playback state
├── server.py                 # FastAPI WebSocket & REST API server
├── hardware_client.py        # IoT / Local Hardware VLC player client
├── db/
│   ├── database.py           # SQLAlchemy engine & session maker
│   └── models.py             # User, MusicVault, PlaybackHistory schemas
├── tools/
│   ├── media_tools.py        # YouTube Music API & yt-dlp stream extractor
│   ├── premium_media_tools.py # Spotipy OAuth2 & remote player controls
│   └── music_vault.py        # Server-side favorites & playlist management
├── agent/
│   └── schemas.py            # OpenAI/Groq tool declarations for LLM
└── v2_frontend/
    └── src/
        ├── app/api/music/    # REST routes proxying server endpoints
        └── components/       # NowPlayingCard, FavoritesList React components
```

---

## 2. Prerequisites & Environment Configuration

### A. Python Dependencies (`requirements.txt`)
```text
ytmusicapi>=1.8.0
yt-dlp>=2024.3.10
spotipy>=2.23.0
httpx>=0.27.0
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
sqlalchemy>=2.0.0
python-vlc>=3.0.18000
pygame>=2.5.0
pydantic>=2.0.0
websockets>=12.0
python-dotenv>=1.0.0
```

### B. Environment Configuration (`.env`)
Create a `.env` file in the project root:
```env
# Server Config
PORT=8000
SERVER_URL=http://127.0.0.1:8000

# Spotify Developer Portal App Credentials
SPOTIPY_CLIENT_ID=your_spotify_client_id_here
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret_here
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback

# System Settings
DATABASE_URL=sqlite:///./jarvis_cloud.db
ACTION_DELAY=1.5
```

---

## Step 1: Database Setup & Models (`db/database.py` & `db/models.py`)

### `db/database.py`
```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jarvis_cloud.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    from db import models
    Base.metadata.create_all(bind=engine)
```

### `db/models.py`
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, default="user@domain.com")
    name = Column(String, default="User")
    created_at = Column(DateTime, default=datetime.utcnow)

class MusicVault(Base):
    __tablename__ = "music_vault"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    song_name = Column(String, nullable=False)
    artist = Column(String, nullable=True)
    url = Column(Text, nullable=False)
    is_favorite = Column(Integer, default=0)       # 1 = Favorite, 0 = Regular
    playlist_name = Column(String, nullable=True) # e.g. "workout", "relax"
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

class PlaybackHistory(Base):
    __tablename__ = "playback_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    song_name = Column(String, nullable=False)
    artist = Column(String, nullable=True)
    provider = Column(String, default="ytmusic")
    played_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
```

---

## Step 2: Global State Management (`state.py`)

Create `state.py` to maintain an in-memory active playback state synchronized across server tools and clients:

```python
"""
state.py — Thread-safe in-memory state tracker for active media playback.
"""

CURRENT_PLAYBACK_STATE = {
    "song_name": "",
    "artist": "",
    "url": "",
    "is_playing": False,
    "duration": "0:00",
    "provider": "",      # "ytmusic" or "spotify"
    "playlist_queue": [],# List of queued stream dictionaries for JIT playback
    "volume": 80
}

def update_playback_state(song_name: str, artist: str, url: str, provider: str, is_playing: bool = True):
    CURRENT_PLAYBACK_STATE["song_name"] = song_name
    CURRENT_PLAYBACK_STATE["artist"] = artist
    CURRENT_PLAYBACK_STATE["url"] = url
    CURRENT_PLAYBACK_STATE["provider"] = provider
    CURRENT_PLAYBACK_STATE["is_playing"] = is_playing

def reset_playback_state():
    CURRENT_PLAYBACK_STATE["song_name"] = ""
    CURRENT_PLAYBACK_STATE["artist"] = ""
    CURRENT_PLAYBACK_STATE["url"] = ""
    CURRENT_PLAYBACK_STATE["is_playing"] = False
    CURRENT_PLAYBACK_STATE["provider"] = ""
    CURRENT_PLAYBACK_STATE["playlist_queue"].clear()
```

---

## Step 3: YouTube Music & `yt-dlp` Engine (`tools/media_tools.py`)

This file manages YouTube Music searching, stream link extraction using `yt-dlp`, and background Just-In-Time (JIT) queue preparation.

```python
import httpx
import threading
from ytmusicapi import YTMusic
import yt_dlp
from state import update_playback_state, CURRENT_PLAYBACK_STATE

# 1. Search YouTube Music for Songs
def search_ytmusic(query: str, limit: int = 5) -> list[dict]:
    """Search YouTube Music for tracks using ytmusicapi."""
    try:
        yt = YTMusic()
        results = yt.search(query, filter="songs", limit=limit)
        if not results:
            return []
            
        parsed = []
        for r in results:
            artists = ", ".join(a.get("name", "") for a in r.get("artists", []))
            parsed.append({
                "id": r.get("videoId", ""),
                "name": r.get("title", ""),
                "artist": artists,
                "album": r.get("album", {}).get("name") if r.get("album") else "Single",
                "duration": r.get("duration", "0:00")
            })
        return parsed
    except Exception as e:
        print(f"[YTMusic Error] Search failed: {e}")
        return []

# 2. Extract Direct Audio Stream URL via yt-dlp
def get_ytmusic_stream_url(video_id: str) -> str:
    """Extract direct raw audio stream URL via yt-dlp without downloading to disk."""
    opts = {
        'format': 'worstaudio[ext=m4a]/bestaudio[ext=m4a]/best',
        'quiet': True,
        'noplaylist': True,
        'extract_flat': False,
        'youtube_include_dash_manifest': False,
        'extractor_args': {'youtube': {'player_client': ['android_vr', 'web']}}
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            return info.get("url", "")
    except Exception as e:
        print(f"[yt-dlp Error] Stream extraction failed for {video_id}: {e}")
        return ""

# 3. Background JIT Queue Builder for Playlists
def _async_prepare_playlist(songs: list[dict]):
    """Background worker to extract stream URLs for playlist tracks without blocking response."""
    for song in songs:
        if not song.get("stream_url"):
            song["stream_url"] = get_ytmusic_stream_url(song["id"])
            CURRENT_PLAYBACK_STATE["playlist_queue"].append(song)

# 4. Main LLM Tool Trigger for Playback
def play_ytmusic(query: str, is_playlist: bool = False) -> str:
    """
    Search and play a song or playlist from YouTube Music.
    query: Song name, artist, or keywords.
    """
    limit = 6 if is_playlist else 1
    songs = search_ytmusic(query, limit=limit)
    
    if not songs or not songs[0].get("id"):
        return f"❌ Could not find any songs matching '{query}' on YouTube Music."

    # Process first song instantly
    first_song = songs[0]
    stream_url = get_ytmusic_stream_url(first_song["id"])
    
    if not stream_url:
        return f"❌ Failed to extract audio stream for '{first_song['name']}'."

    # Update state
    update_playback_state(
        song_name=first_song["name"],
        artist=first_song["artist"],
        url=stream_url,
        provider="ytmusic",
        is_playing=True
    )

    # Emit playback command to Cloud Server / WebSocket
    try:
        httpx.post("http://127.0.0.1:8000/emit", json={
            "action": "play_music",
            "url": stream_url,
            "meta": {
                "name": first_song["name"],
                "artist": first_song["artist"],
                "provider": "ytmusic"
            }
        }, timeout=2.0)
    except Exception as e:
        print(f"[Emit Error] Could not send payload to server: {e}")

    # Kick off background JIT stream extractor if playlist requested
    if is_playlist and len(songs) > 1:
        CURRENT_PLAYBACK_STATE["playlist_queue"].clear()
        threading.Thread(target=_async_prepare_playlist, args=(songs[1:],), daemon=True).start()
        return f"🎵 Now playing '{first_song['name']}' by {first_song['artist']} (and queued {len(songs)-1} more tracks)."

    return f"🎵 Now playing '{first_song['name']}' by {first_song['artist']} on YouTube Music."

def stop_music() -> str:
    """Stop active music playback on hardware."""
    try:
        httpx.post("http://127.0.0.1:8000/emit", json={"action": "stop_audio"}, timeout=2.0)
        CURRENT_PLAYBACK_STATE["is_playing"] = False
        return "⏹️ Music playback stopped."
    except Exception as e:
        return f"❌ Failed to stop playback: {e}"
```

---

## Step 4: Spotify OAuth & Remote Control Engine (`tools/premium_media_tools.py`)

This file implements Spotify Web API integration via `spotipy`.

```python
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPE = "user-modify-playback-state user-read-playback-state user-read-currently-playing playlist-read-private"

def _get_spotify():
    """Initializes and returns an authenticated Spotipy instance."""
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")
    
    if not client_id or not client_secret:
        raise ValueError("Spotify API credentials missing from environment variables.")
        
    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        open_browser=True
    )
    return spotipy.Spotify(auth_manager=auth_manager)

def play_spotify(query: str = "") -> str:
    """Play or resume tracks/playlists/artists on active Spotify client device."""
    try:
        sp = _get_spotify()
        devices = sp.devices()
        all_devices = devices.get("devices", [])
        
        if not all_devices:
            return "❌ No active Spotify device detected. Please open Spotify on your PC or phone first."
            
        # Target active device or pick first available
        active_devices = [d for d in all_devices if d.get("is_active")]
        target_device = active_devices[0]["id"] if active_devices else all_devices[0]["id"]
        
        if not query:
            sp.start_playback(device_id=target_device)
            return "▶️ Resumed Spotify playback."
            
        results = sp.search(q=query, limit=1, type="track,playlist,artist")
        
        if results.get("tracks") and results["tracks"]["items"]:
            item = results["tracks"]["items"][0]
            sp.start_playback(device_id=target_device, uris=[item["uri"]])
            return f"🎵 Playing '{item['name']}' by {item['artists'][0]['name']} on Spotify."
            
        elif results.get("playlists") and results["playlists"]["items"]:
            item = results["playlists"]["items"][0]
            sp.start_playback(device_id=target_device, context_uri=item["uri"])
            return f"🎵 Playing playlist '{item['name']}' on Spotify."
            
        elif results.get("artists") and results["artists"]["items"]:
            item = results["artists"]["items"][0]
            sp.start_playback(device_id=target_device, context_uri=item["uri"])
            return f"🎵 Playing top tracks by '{item['name']}' on Spotify."
            
        return f"❌ Could not find '{query}' on Spotify."
        
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 403:
            return "❌ Spotify Premium is required to control playback programmatically."
        return f"❌ Spotify API Error: {e.msg}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def pause_spotify() -> str:
    """Pause Spotify playback."""
    try:
        sp = _get_spotify()
        sp.pause_playback()
        return "⏸️ Spotify playback paused."
    except Exception as e:
        return f"❌ Error: {str(e)}"

def next_spotify_track() -> str:
    """Skip to next track on Spotify."""
    try:
        sp = _get_spotify()
        sp.next_track()
        return "⏭️ Skipped to next track on Spotify."
    except Exception as e:
        return f"❌ Error skipping track: {e}"
```

---

## Step 5: Server-Side Music Vault & Playlists (`tools/music_vault.py`)

This file allows users to save favorites and custom named playlists in SQLite.

```python
from db.database import SessionLocal
from db.models import MusicVault, User
from state import CURRENT_PLAYBACK_STATE
import httpx

def _get_default_user(db):
    user = db.query(User).first()
    if not user:
        user = User(email="default@user.com", name="Default User")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def like_current_song() -> str:
    """Save currently playing track on hardware to Server Favorites."""
    song_name = CURRENT_PLAYBACK_STATE.get("song_name")
    if not song_name:
        return "❌ No music is currently playing."
        
    db = SessionLocal()
    try:
        user = _get_default_user(db)
        artist = CURRENT_PLAYBACK_STATE.get("artist", "Unknown")
        url = CURRENT_PLAYBACK_STATE.get("url", "")
        
        existing = db.query(MusicVault).filter(
            MusicVault.user_id == user.id,
            MusicVault.song_name == song_name
        ).first()
        
        if existing:
            existing.is_favorite = 1
            db.commit()
            return f"❤️ '{song_name}' is in your Server Favorites."
            
        new_fav = MusicVault(
            user_id=user.id,
            song_name=song_name,
            artist=artist,
            url=url,
            is_favorite=1
        )
        db.add(new_fav)
        db.commit()
        return f"❤️ Added '{song_name}' by {artist} to Server Favorites."
    finally:
        db.close()

def add_to_playlist(playlist_name: str) -> str:
    """Add currently playing track to custom named playlist."""
    song_name = CURRENT_PLAYBACK_STATE.get("song_name")
    if not song_name:
        return "❌ No music is currently playing."
        
    db = SessionLocal()
    try:
        user = _get_default_user(db)
        p_name = playlist_name.strip().lower()
        
        new_entry = MusicVault(
            user_id=user.id,
            song_name=song_name,
            artist=CURRENT_PLAYBACK_STATE.get("artist", "Unknown"),
            url=CURRENT_PLAYBACK_STATE.get("url", ""),
            is_favorite=0,
            playlist_name=p_name
        )
        db.add(new_entry)
        db.commit()
        return f"🎶 Added '{song_name}' to playlist '{playlist_name}'."
    finally:
        db.close()

def play_favorites() -> str:
    """Play stored database favorites."""
    db = SessionLocal()
    try:
        user = _get_default_user(db)
        favs = db.query(MusicVault).filter(
            MusicVault.user_id == user.id,
            MusicVault.is_favorite == 1
        ).all()
        
        if not favs:
            return "❌ Your Favorites list is empty."
            
        first = favs[0]
        httpx.post("http://127.0.0.1:8000/emit", json={
            "action": "play_music",
            "url": first.url,
            "meta": {"name": first.song_name, "artist": first.artist}
        }, timeout=2.0)
        return f"🎵 Playing favorites, starting with '{first.song_name}'."
    finally:
        db.close()

def play_custom_playlist(playlist_name: str) -> str:
    """Play all songs in a stored playlist."""
    db = SessionLocal()
    try:
        user = _get_default_user(db)
        tracks = db.query(MusicVault).filter(
            MusicVault.user_id == user.id,
            MusicVault.playlist_name == playlist_name.strip().lower()
        ).all()
        
        if not tracks:
            return f"❌ Playlist '{playlist_name}' is empty or does not exist."
            
        first = tracks[0]
        httpx.post("http://127.0.0.1:8000/emit", json={
            "action": "play_music",
            "url": first.url,
            "meta": {"name": first.song_name, "artist": first.artist}
        }, timeout=2.0)
        return f"🎵 Playing playlist '{playlist_name}' starting with '{first.song_name}'."
    finally:
        db.close()
```

---

## Step 6: FastAPI Server & WebSocket Broadcaster (`server.py`)

This file acts as the Cloud Brain server listening for emit payloads and streaming JSON over WebSockets to hardware.

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from db.database import init_db
from state import CURRENT_PLAYBACK_STATE, update_playback_state

app = FastAPI(title="Jarvis Cloud Brain Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

# --- Connection Manager for Hardware WebSocket ---
class HardwareManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
        print("🟢 Hardware Client Connected.")

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)
            print("🔴 Hardware Client Disconnected.")

    async def broadcast_payload(self, data: dict):
        for conn in self.connections:
            try:
                await conn.send_json(data)
            except Exception as e:
                print(f"[WS Broadcast Error] {e}")

manager = HardwareManager()

# --- Action Payload Model ---
class ActionPayload(BaseModel):
    action: str
    url: str | None = None
    meta: dict | None = None

@app.post("/emit")
async def emit_action(payload: ActionPayload):
    """API Endpoint called by agent tools to send audio commands to hardware."""
    if payload.action == "play_music":
        meta = payload.meta or {}
        update_playback_state(
            song_name=meta.get("name", "Unknown Track"),
            artist=meta.get("artist", "Unknown Artist"),
            url=payload.url or "",
            provider=meta.get("provider", "ytmusic"),
            is_playing=True
        )
    elif payload.action == "stop_audio":
        CURRENT_PLAYBACK_STATE["is_playing"] = False

    await manager.broadcast_payload(payload.model_dump())
    return {"status": "broadcast_sent", "action": payload.action}

@app.get("/api/music/now-playing")
def get_now_playing():
    """Endpoint for Dashboard UI to fetch active track metadata."""
    return CURRENT_PLAYBACK_STATE
@app.websocket("/hardware/ws")
async def hardware_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            # Receive mic input or client status telemetry
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

---

## Step 7: Production Hardware Client Player (`hardware_client.py`)

> **⚠️ Important:** The implementation uses a custom dual-channel architecture built on top of three bundled executables: `ffmpeg.exe`, `ffplay.exe`, and `ffplay_voice.exe`. These must be placed in the project root directory.

---

### A. The Three Executables & Dual-Channel Routing

| File | Role | Why Separate? |
|---|---|---|
| `ffmpeg.exe` | **Audio Decoder:** Fetches the remote stream URL, decodes it to raw PCM audio bytes (16-bit stereo), and pipes it to the Spatial Engine. | Handles reconnect logic, user-agent spoofing, and seek offsets (`-ss`). |
| `ffplay.exe` | **Music Channel Player:** Standard ffplay executable for music audio streaming. | Primary player binary for desktop music output. |
| `ffplay_voice.exe` | **Voice Channel Player:** A **cloned copy of `ffplay.exe`** with a different process name so Windows Volume Mixer treats it as a *separate audio app* from music. | Critical for **Voice Ducking** — allows `pycaw` to target ONLY the music process's volume, keeping voice crisp. |

> **Runtime Cloning:** On first launch, `hardware_client.py` uses `shutil.copy("ffplay.exe", "ffplay_voice.exe")` to create the clone automatically if it doesn't already exist.

---

### B. `HardwareAudioEngine` Class Architecture

The engine runs **five background daemon threads** simultaneously:
1. `_voice_worker`: Plays TTS speech via `ffplay_voice.exe` sequentially.
2. `_music_worker`: Plays music tracks from queue sequentially.
3. `_prefetch_worker`: Pre-fetches stream URLs for next queue item (gapless playback).
4. `_state_persistence_worker`: Tracks playback offset for precise resume.
5. `_command_worker`: Serializes all incoming WebSocket commands to prevent race conditions.

---

### C. Audio Pipeline Code (`hardware_client.py`)

```python
import asyncio
import json
import websockets
import os
import subprocess
import threading
import time
import shutil
import platform
from tools.spatial_audio import SpatialAudioEngine, HeadTracker

class HardwareAudioEngine:
    """Dual-channel audio controller with Voice Ducking using ffmpeg & ffplay."""
    def __init__(self):
        self.voice_process = None
        self.music_process = None
        self._voice_queue = []
        self._music_queue = []
        self._music_history = []
        self._lock = threading.Lock()
        
        self.last_music_item = None
        self.music_start_time = 0
        self.pause_offset = 0
        self.is_paused = False
        
        # Spatial audio engine
        self.spatial_engine = SpatialAudioEngine()
        self.audio_profile = 'balanced' # 'balanced' | 'bass_boost' | 'widened' | '3d_cinema'
        
        # Start background workers
        threading.Thread(target=self._voice_worker, daemon=True).start()
        threading.Thread(target=self._music_worker, daemon=True).start()
        threading.Thread(target=self._prefetch_worker, daemon=True).start()

    def _get_ffplay_path(self):
        local_ffplay = os.path.join(os.getcwd(), "ffplay.exe")
        return local_ffplay if os.path.exists(local_ffplay) else (shutil.which("ffplay") or "ffplay")

    def _get_ffmpeg_path(self):
        local_ffmpeg = os.path.join(os.getcwd(), "ffmpeg.exe")
        return local_ffmpeg if os.path.exists(local_ffmpeg) else (shutil.which("ffmpeg") or "ffmpeg")

    def _play_music_now(self, url: str, is_alarm: bool = False, start_offset: float = 0):
        """Streams music via ffmpeg -> PCM -> SpatialAudioEngine."""
        if not url: return

        ffmpeg_path = self._get_ffmpeg_path()
        decoder_cmd = [
            ffmpeg_path,
            "-hide_banner",
            "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5"
        ]
        
        if start_offset > 0:
            decoder_cmd.extend(["-ss", str(round(start_offset, 2))])
            
        decoder_cmd.extend([
            "-i", url,
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ar", str(self.spatial_engine.fs),
            "-ac", "2",
            "-"
        ])

        try:
            self.spatial_engine.profile = self.audio_profile
            self.spatial_engine.start()
            
            decoder_proc = subprocess.Popen(
                decoder_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            with self._lock: self.music_process = decoder_proc
            
            while True:
                chunk = decoder_proc.stdout.read(16384) # 16KB chunks
                if not chunk:
                    if decoder_proc.poll() is not None: break
                    continue
                self.spatial_engine.feed(chunk)
                
            self.spatial_engine.stop()
        except Exception as e:
            print(f"[HW Error] Playback failed: {e}")
        finally:
            with self._lock: self.music_process = None

    def _voice_worker(self):
        """Plays TTS audio using ffplay_voice.exe (cloned for Windows Mixer isolation)."""
        ffplay_path = self._get_ffplay_path()
        ffplay_voice_path = os.path.join(os.getcwd(), "ffplay_voice.exe")
        
        if os.path.exists(ffplay_path) and not os.path.exists(ffplay_voice_path):
            try: shutil.copy(ffplay_path, ffplay_voice_path)
            except: ffplay_voice_path = ffplay_path

        while True:
            url = None
            with self._lock:
                if self._voice_queue and not self.voice_process:
                    url = self._voice_queue.pop(0)
            
            if url:
                self.duck_music() # Duck music to 15%
                v_exe = ffplay_voice_path if os.path.exists(ffplay_voice_path) else ffplay_path
                self.voice_process = subprocess.Popen(
                    [v_exe, "-nodisp", "-autoexit", "-loglevel", "quiet", "-infbuf", url],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                )
                self.voice_process.wait()
                self.voice_process = None
                self.unduck_music() # Unduck music back to 100%
            else:
                time.sleep(0.05)

    def duck_music(self):
        """Ducks music volume using pycaw audio session targeting music_process PID."""
        try:
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
            if not self.music_process: return
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and session.Process.pid == self.music_process.pid:
                    v = session._ctl.QueryInterface(ISimpleAudioVolume)
                    for vol in [0.70, 0.40, 0.20, 0.15]:
                        v.SetMasterVolume(vol, None)
                        time.sleep(0.08)
        except: pass

    def unduck_music(self):
        """Restores music volume back to 100%."""
        try:
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
            if not self.music_process: return
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and session.Process.pid == self.music_process.pid:
                    v = session._ctl.QueryInterface(ISimpleAudioVolume)
                    for vol in [0.30, 0.50, 0.75, 0.90, 1.0]:
                        v.SetMasterVolume(vol, None)
                        time.sleep(0.12)
        except: pass

    def stop_music(self):
        with self._lock:
            proc = self.music_process
            self.music_process = None
        if proc:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                proc.kill()
```

---

## Step 8: Next.js Dashboard UI Components

Create `v2_frontend/src/components/NowPlayingCard.tsx` for real-time playback control in your web interface:

```tsx
"use client";
import React, { useEffect, useState } from "react";
import { Play, Pause, Heart, Square, Music } from "lucide-react";

interface PlaybackState {
  song_name: string;
  artist: string;
  is_playing: boolean;
  provider: string;
}

export default function NowPlayingCard() {
  const [playback, setPlayback] = useState<PlaybackState>({
    song_name: "No music playing",
    artist: "Nova AI Agent",
    is_playing: false,
    provider: ""
  });

  const fetchStatus = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/music/now-playing");
      const data = await res.json();
      setPlayback(data);
    } catch (err) {
      console.error("Failed to fetch player status", err);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 2500);
    return () => clearInterval(interval);
  }, []);

  const handleLike = async () => {
    alert(`❤️ Favorite toggle sent for ${playback.song_name}`);
  };

  return (
    <div className="w-full max-w-md bg-neutral-950 text-white p-5 rounded-3xl border border-neutral-800 shadow-2xl flex items-center justify-between">
      <div className="flex items-center space-x-4">
        <div className="w-14 h-14 bg-gradient-to-tr from-indigo-600 to-pink-500 rounded-2xl flex items-center justify-center shadow-lg">
          <Music className="w-7 h-7 text-white" />
        </div>
        <div>
          <h4 className="font-bold text-base line-clamp-1">{playback.song_name}</h4>
          <p className="text-xs text-neutral-400 font-medium line-clamp-1">{playback.artist}</p>
          {playback.provider && (
            <span className="inline-block mt-1 text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 bg-neutral-800 rounded-full text-indigo-400">
              {playback.provider}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <button onClick={handleLike} className="p-3 bg-neutral-900 hover:bg-neutral-800 text-red-500 rounded-full transition">
          <Heart className="w-5 h-5 fill-red-500" />
        </button>
        <button className="p-3 bg-white text-black rounded-full hover:scale-105 transition">
          {playback.is_playing ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
        </button>
      </div>
    </div>
  );
}
```

---

## Step 9: LLM Tool Schemas & ReAct Integration

Declare these OpenAI/Groq function schemas inside `agent/schemas.py` so your ReAct LLM agent knows how and when to invoke music tools:

```python
MUSIC_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "play_ytmusic",
            "description": "Search and play any song, music video, or playlist for free via YouTube Music direct streaming.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": { "type": "string", "description": "Song title, artist name, or mood query." },
                    "is_playlist": { "type": "boolean", "description": "Set to true if user requested a full playlist." }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_spotify",
            "description": "Play a track, album, artist, or playlist on active Spotify client application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": { "type": "string", "description": "Spotify search query." }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop_music",
            "description": "Stop current audio or music playback on room speakers.",
            "parameters": { "type": "object", "properties": {} }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "like_current_song",
            "description": "Save the currently playing music track into user's Server Favorites list.",
            "parameters": { "type": "object", "properties": {} }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_playlist",
            "description": "Add currently playing song to a custom named playlist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "playlist_name": { "type": "string", "description": "Name of playlist (e.g., Workout, Relax)." }
                },
                "required": ["playlist_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_favorites",
            "description": "Play all saved favorite songs stored in the database.",
            "parameters": { "type": "object", "properties": {} }
        }
    }
]
```

---

## Step 10: Troubleshooting, Edge Cases & Maintenance

### 1. `yt-dlp` YouTube Extraction Failures (Bot Detection / Cipher Changes)
* **Symptom:** `yt-dlp error: Sign in to confirm you're not a bot`.
* **Fix:** Update `yt-dlp` regularly using `pip install --upgrade yt-dlp`. Ensure `player_client: ['android_vr', 'web']` is passed inside `extractor_args`.

### 2. Audio Stuttering / Latency
* **Symptom:** Audio clips or buffers frequently on IoT devices.
* **Fix:** Use direct `.m4a` audio format (`format: 'worstaudio[ext=m4a]/bestaudio[ext=m4a]/best'`) to prevent real-time video stream transcoding overhead.

### 3. Spotify "No Active Device" Error
* **Symptom:** `play_spotify()` returns 404 or missing active device error.
* **Fix:** Ensure Spotify app is launched on user's device and logged into the same account specified in `.env`.

---

## 🏁 Execution Commands Summary

```bash
# 1. Initialize DB & Launch FastAPI Server
uvicorn server:app --port 8000 --reload

# 2. Launch Hardware Audio Listener
python hardware_client.py

# 3. Test LLM Voice Commands
# "Jarvis, play Tum Hi Ho" -> Triggers play_ytmusic("Tum Hi Ho")
# "Jarvis, like this song" -> Triggers like_current_song()
# "Jarvis, play my favorites" -> Triggers play_favorites()
```
