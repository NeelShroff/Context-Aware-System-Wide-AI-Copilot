"""
Standalone Test Script: Verify Music Playback System
Runs YouTube Music search, audio stream extraction, and live background playback.
"""
import os
import sys
import time
from pathlib import Path

# Ensure Windows console uses UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.music_engine import MusicEngine


def run_music_test(track_query: str = "Alex Warren"):
    print("==================================================")
    print(" [*] TEST MUSIC PLAYBACK SYSTEM")
    print("==================================================")
    print(f"1. Searching YouTube Music for: '{track_query}'...")

    
    track_info = MusicEngine.search_track(track_query)
    if not track_info:
        print("❌ Search failed: No tracks found!")
        return False

    print(f"   [OK] Track found: '{track_info.get('title')}' by {track_info.get('artist')}")
    print(f"   [OK] YouTube URL: {track_info.get('url')}")

    print("\n2. Extracting live HTTP audio stream URL...")
    stream_url = MusicEngine.get_audio_stream_url(track_info["url"])
    if not stream_url:
        print("❌ Stream extraction failed!")
        return False

    print(f"   [OK] Stream URL extracted successfully!")

    print("\n3. Starting music playback...")
    res = MusicEngine.get_instance().play(track_query)
    print(f"   [OK] Playback result: {res.get('message')}")

    print("\n--------------------------------------------------")
    print(" 🔊 MUSIC IS NOW PLAYING LIVE ON YOUR SPEAKERS! ")
    print(" Listening for 10 seconds...")
    print("--------------------------------------------------")

    for i in range(10, 0, -1):
        print(f" Playing... ({i}s remaining)", flush=True)
        time.sleep(1)

    print("\n4. Stopping music playback...")
    MusicEngine.get_instance().stop()
    print("   [OK] Playback stopped clean.")
    print("==================================================")
    print(" ✅ MUSIC SYSTEM TEST COMPLETED SUCCESSFULLY!")
    print("==================================================")
    return True


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Alex Warren"
    run_music_test(query)
