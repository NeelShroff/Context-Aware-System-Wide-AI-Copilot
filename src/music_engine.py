"""
YouTube Music Streaming Engine.
Provides voice-controlled music search, stream extraction (ytmusicapi / yt-dlp),
and native audio playback control using PyQt5 QMediaPlayer.
"""
import os
import sys
import json
import time
import logging
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


logger = logging.getLogger("MusicEngine")
logger.setLevel(logging.INFO)

from src.tts_engine import announce_music_start


def get_no_window_kwargs() -> dict:
    """Returns creationflags and startupinfo for 100% windowless execution on Windows."""
    kwargs = {}
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    return kwargs


class MusicEngine:

    """Singleton Music Playback Engine supporting search, streaming, and controls."""

    _instance = None
    _lock = threading.Lock()
    _stream_cache: Dict[str, str] = {}

    def __init__(self):
        self.current_track: Optional[Dict[str, Any]] = None
        self.is_playing: bool = False
        self.is_paused: bool = False
        self._player = None
        self._qt_app = None
        self._playback_thread: Optional[threading.Thread] = None
        self._init_qt_player()

    @classmethod
    def get_instance(cls) -> "MusicEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _init_qt_player(self):
        """Initializes PyQt5 QMediaPlayer engine."""
        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtMultimedia import QMediaPlayer
            
            if QApplication.instance() is None:
                self._qt_app = QApplication(sys.argv)
            else:
                self._qt_app = QApplication.instance()

            self._player = QMediaPlayer()
            self._player.setVolume(85)
        except Exception as e:
            logger.warning(f"PyQt5 QMediaPlayer initialization notice: {e}")
            self._player = None

    @staticmethod
    def search_track(query: str) -> Optional[Dict[str, Any]]:
        """Searches YouTube Music for track query and returns metadata dict."""
        query_clean = query.strip()
        if not query_clean:
            return None

        # 1. Try ytmusicapi first
        try:
            from ytmusicapi import YTMusic
            yt = YTMusic()
            results = yt.search(query_clean, filter="songs")
            if results:
                top = results[0]
                video_id = top.get("videoId")
                title = top.get("title", "Unknown Track")
                artists = ", ".join([a.get("name", "") for a in top.get("artists", []) if isinstance(a, dict)])
                return {
                    "video_id": video_id,
                    "title": title,
                    "artist": artists,
                    "url": f"https://www.youtube.com/watch?v={video_id}"
                }
        except Exception as e:
            logger.warning(f"ytmusicapi search error: {e}")

        # 2. Fallback to yt-dlp search
        try:
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "--default-search", "ytsearch1",
                "--dump-json", f"ytsearch1:{query_clean}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15, **get_no_window_kwargs())
            if res.returncode == 0 and res.stdout.strip():
                meta = json.loads(res.stdout.strip())
                return {
                    "video_id": meta.get("id"),
                    "title": meta.get("title", query_clean),
                    "artist": meta.get("uploader", "YouTube"),
                    "url": meta.get("webpage_url") or f"https://www.youtube.com/watch?v={meta.get('id')}"
                }
        except Exception as e:
            logger.warning(f"yt-dlp fallback search error: {e}")

        return None

    @classmethod
    def get_audio_stream_url(cls, youtube_url: str) -> Optional[str]:
        """Extracts direct m4a/audio HTTP stream URL using in-memory yt_dlp without writing files to disk."""
        if youtube_url in cls._stream_cache:
            return cls._stream_cache[youtube_url]

        try:
            import yt_dlp
            opts = {
                'format': 'worstaudio[ext=m4a]/bestaudio[ext=m4a]/best',
                'quiet': True,
                'noplaylist': True,
                'extract_flat': False,
                'youtube_include_dash_manifest': False,
                'extractor_args': {'youtube': {'player_client': ['android_vr', 'web']}}
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                url = info.get("url", "")
                if url:
                    cls._stream_cache[youtube_url] = url
                    return url
        except Exception as e:
            logger.warning(f"In-memory yt_dlp extraction notice: {e}")

        # Fallback to subprocess yt-dlp
        try:
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "-g", "-f", "bestaudio/best",
                youtube_url
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10, **get_no_window_kwargs())
            if res.returncode == 0 and res.stdout.strip():
                url = res.stdout.strip().splitlines()[0]
                cls._stream_cache[youtube_url] = url
                return url
        except Exception as e:
            logger.error(f"Subprocess stream extraction error: {e}")

        return None


    def play(self, query: str) -> Dict[str, Any]:
        """Searches track, extracts stream, and starts detached background playback."""
        track_info = self.search_track(query)
        if not track_info or not track_info.get("url"):
            return {"success": False, "message": f"No tracks found for '{query}'."}

        daemon_script = Path(__file__).resolve().parent / "music_player_daemon.py"
        py_exe = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(py_exe):
            py_exe = sys.executable

        # Stop existing player daemon first
        self.stop()

        # Spawn detached background process so music continues playing after main.py exits
        try:
            cmd = [py_exe, str(daemon_script), "--play", query]
            kwargs = get_no_window_kwargs()
            if sys.platform == "win32":
                # Add DETACHED_PROCESS flag for independent background execution
                kwargs["creationflags"] = kwargs.get("creationflags", 0) | 0x00000008

            subprocess.Popen(cmd, **kwargs)

            self.is_playing = True
            self.is_paused = False
            self.current_track = track_info

            return {
                "success": True,
                "message": f"Now playing: {track_info['title']} by {track_info['artist']}",
                "track": track_info
            }
        except Exception as e:
            logger.error(f"Failed to launch music daemon: {e}")
            return {"success": False, "message": f"Music playback error: {e}"}

    def pause(self) -> Dict[str, Any]:
        """Pauses currently playing music."""
        return self.stop()

    def resume(self) -> Dict[str, Any]:
        """Resumes paused music playback."""
        return {"success": False, "message": "Use play command to start music."}

    def stop(self) -> Dict[str, Any]:
        """Stops music playback completely."""
        daemon_script = Path(__file__).resolve().parent / "music_player_daemon.py"
        try:
            subprocess.run([sys.executable, str(daemon_script), "--stop"], capture_output=True, timeout=5, **get_no_window_kwargs())
        except Exception:
            pass

        self.is_playing = False
        self.is_paused = False
        self.current_track = None
        return {"success": True, "message": "Music stopped."}
