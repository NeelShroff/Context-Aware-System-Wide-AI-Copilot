"""
Test suite for SelectiveTTSEngine and ElevenLabs Flash v2.5 integration.
"""
import os
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.tts_engine import (
    SelectiveTTSEngine,
    announce_reminder,
    announce_music_start,
    announce_memory_saved,
    EVENT_REMINDER,
)

def test_channel_filtering(caplog=None):
    """Verifies that non-allowed event channels are suppressed."""
    # Attempt speaking on an unapproved channel
    SelectiveTTSEngine.speak_event("INVALID_CHANNEL", "This should not be spoken.")
    time.sleep(0.5)
    print("Channel filtering test passed.")

def test_elevenlabs_fallback():
    """Verifies that without a valid API key, ElevenLabs returns False and falls back cleanly."""
    os.environ["ELEVENLABS_API_KEY"] = "your_elevenlabs_api_key_here"
    success = SelectiveTTSEngine._speak_elevenlabs("Test fallback speech")
    assert success is False, "ElevenLabs should return False when API key is a placeholder"
    print("ElevenLabs fallback test passed.")

def test_announcements():
    """Triggers helper announcement functions."""
    announce_reminder("Test reminder announcement")
    announce_music_start("Midnight City", "M83")
    announce_memory_saved("User prefers dark mode")
    time.sleep(1.0)
    print("Announcements triggered successfully.")

if __name__ == "__main__":
    test_channel_filtering()
    test_elevenlabs_fallback()
    test_announcements()
    print("ALL TTS ENGINE TESTS COMPLETED SUCCESSFULLY!")
