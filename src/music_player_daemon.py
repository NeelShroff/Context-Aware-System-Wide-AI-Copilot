"""
Standalone Background Music Player Daemon for System-Wide AI Copilot.
Runs as a detached Windows process so music playback continues playing indefinitely
even after single-shot CLI commands or main.py scripts complete and exit.
"""
import os
import sys
import json
import time
import signal
import logging
import argparse
import subprocess
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("MusicDaemon")
logger.setLevel(logging.INFO)

PID_FILE = Path(__file__).resolve().parent.parent / "data" / "music_daemon.pid"
META_FILE = Path(__file__).resolve().parent.parent / "data" / "music_daemon_meta.json"


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


def kill_existing_daemon():
    """Kills any running music daemon process or active ffplay player on Windows."""
    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            import ctypes
            PROCESS_TERMINATE = 1
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if handle:
                ctypes.windll.kernel32.TerminateProcess(handle, 0)
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            pass
        try:
            os.remove(PID_FILE)
        except Exception:
            pass

    # Kill active ffplay player processes 100% silently
    try:
        subprocess.run(["taskkill", "/F", "/IM", "ffplay.exe"], capture_output=True, **get_no_window_kwargs())
    except Exception:
        pass


def play_music_daemon(query: str):
    """Searches track, extracts live stream URL, and launches windowless FFplay player."""
    kill_existing_daemon()

    # Save current PID
    os.makedirs(PID_FILE.parent, exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    from src.music_engine import MusicEngine
    track_info = MusicEngine.search_track(query)
    if not track_info or not track_info.get("url"):
        sys.stderr.write(f"No tracks found for '{query}'\n")
        sys.exit(1)

    stream_url = MusicEngine.get_audio_stream_url(track_info["url"])
    if not stream_url:
        sys.stderr.write(f"Could not extract stream URL for '{track_info['title']}'\n")
        sys.exit(1)

    # Save metadata
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump({"track": track_info, "start_time": time.time()}, f, indent=2)

    # Announce TTS & speech bubble
    try:
        from src.tts_engine import announce_music_start
        announce_music_start(track_info["title"], track_info.get("artist", ""))
    except Exception:
        pass

    try:
        import urllib.request
        speech_payload = json.dumps({
            "text": f"🎵 Playing: {track_info['title']}",
            "duration": 5.0,
            "mode": "TALKING"
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8799/api/speech",
            data=speech_payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=0.5)
    except Exception:
        pass

    # Launch FFplay Engine 100% windowlessly (CREATE_NO_WINDOW + SW_HIDE)
    ffplay_exe = os.path.join(os.getcwd(), "ffplay.exe")
    if not os.path.exists(ffplay_exe):
        import shutil
        ffplay_exe = shutil.which("ffplay") or "ffplay"

    logger.info(f"Launching FFplay primary hardware engine silently: {ffplay_exe}")
    try:
        proc = subprocess.Popen([
            ffplay_exe, "-nodisp", "-autoexit", "-loglevel", "quiet", stream_url
        ], **get_no_window_kwargs())
        proc.wait()
    except Exception as e:
        logger.error(f"FFplay playback execution error: {e}")

    kill_existing_daemon()


def main():
    parser = argparse.ArgumentParser(description="Standalone Music Player Daemon")
    parser.add_argument("--play", help="Track query to search and play")
    parser.add_argument("--stop", action="store_true", help="Stop music playback")

    args = parser.parse_args()

    if args.stop:
        kill_existing_daemon()
        sys.exit(0)

    if args.play:
        play_music_daemon(args.play)


if __name__ == "__main__":
    main()

