"""
Selective Event-Based TTS Speech Engine.
Provides spoken voice announcements restricted strictly to key events
(Reminders firing, Music playback starting, Memory saved confirmations).
Does NOT read out long text rewrites or general desktop answers.
"""
import os
import sys
import threading
import logging
import tempfile
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger("SelectiveTTSEngine")
logger.setLevel(logging.INFO)

# Allowed Event Channels
EVENT_REMINDER = "EVENT_REMINDER"
EVENT_MUSIC_START = "EVENT_MUSIC_START"
EVENT_MEMORY_SAVED = "EVENT_MEMORY_SAVED"

ALLOWED_EVENT_CHANNELS = {EVENT_REMINDER, EVENT_MUSIC_START, EVENT_MEMORY_SAVED}


def get_no_window_kwargs() -> dict:
    """Returns creationflags and startupinfo for windowless execution on Windows."""
    kwargs = {}
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    return kwargs


class SelectiveTTSEngine:
    """Singleton TTS Engine enforcing strict event channel filtering with ElevenLabs Flash v2.5 primary and pyttsx3 fallback."""

    _engine = None
    _lock = threading.Lock()

    @classmethod
    def _init_pyttsx3(cls):
        if cls._engine is None:
            try:
                import pyttsx3
                cls._engine = pyttsx3.init()
                cls._engine.setProperty("rate", 175)
                cls._engine.setProperty("volume", 0.9)
            except Exception as e:
                logger.warning(f"Failed to initialize pyttsx3 TTS engine: {e}")
                cls._engine = False

    @classmethod
    def _speak_elevenlabs(cls, text: str) -> bool:
        """
        Attempts to generate and play human-like voice audio using ElevenLabs Flash v2.5 API.
        Returns True if speech played successfully, False otherwise (triggering fallback).
        """
        api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        if not api_key or api_key == "your_elevenlabs_api_key_here":
            return False

        voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM").strip()
        model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5").strip()

        try:
            import requests
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            }
            payload = {
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }

            response = requests.post(url, json=payload, headers=headers, timeout=8)
            if response.status_code != 200:
                logger.warning(f"ElevenLabs TTS API request returned status {response.status_code}: {response.text}")
                return False

            audio_data = response.content
            if not audio_data:
                return False

            # Save temporary audio file for playback
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name

            # Locate ffplay executable
            project_root = Path(__file__).resolve().parent.parent
            ffplay_exe = os.path.join(project_root, "ffplay_voice.exe")
            if not os.path.exists(ffplay_exe):
                ffplay_exe = os.path.join(project_root, "ffplay.exe")
            if not os.path.exists(ffplay_exe):
                ffplay_exe = shutil.which("ffplay") or "ffplay"

            # Execute silent audio playback
            cmd = [ffplay_exe, "-nodisp", "-autoexit", "-loglevel", "quiet", tmp_path]
            subprocess.run(cmd, capture_output=True, timeout=15, **get_no_window_kwargs())

            # Cleanup temp file
            try:
                os.remove(tmp_path)
            except Exception:
                pass

            logger.info("Successfully spoke event using ElevenLabs Flash v2.5")
            return True

        except Exception as e:
            logger.warning(f"ElevenLabs TTS failed: {e}")
            return False

    @classmethod
    def _speak_pyttsx3(cls, text: str):
        """Fallback offline speech generation using pyttsx3."""
        try:
            cls._init_pyttsx3()
            if cls._engine and cls._engine is not False:
                cls._engine.say(text)
                cls._engine.runAndWait()
        except Exception as e:
            logger.warning(f"pyttsx3 TTS fallback speech error: {e}")

    @classmethod
    def speak_event(cls, event_channel: str, text: str):
        """
        Speaks text aloud ONLY if event_channel is in ALLOWED_EVENT_CHANNELS.
        Executes speech in a background thread to prevent blocking main execution.
        """
        if event_channel not in ALLOWED_EVENT_CHANNELS:
            logger.info(f"TTS suppressed for non-allowed event channel '{event_channel}'")
            return

        if not text or not text.strip():
            return

        def _speak_worker(speech_text: str):
            with cls._lock:
                # Try ElevenLabs Flash v2.5 first
                success = cls._speak_elevenlabs(speech_text)
                if not success:
                    # Fallback to local pyttsx3
                    cls._speak_pyttsx3(speech_text)

        t = threading.Thread(target=_speak_worker, args=(text.strip(),), daemon=True)
        t.start()




def announce_reminder(reminder_text: str):
    """Speaks a reminder notification aloud."""
    SelectiveTTSEngine.speak_event(EVENT_REMINDER, f"Reminder: {reminder_text}")


def announce_music_start(track_name: str, artist: str = ""):
    """Speaks music start notification aloud."""
    msg = f"Now playing: {track_name}" if not artist else f"Now playing: {track_name} by {artist}"
    SelectiveTTSEngine.speak_event(EVENT_MUSIC_START, msg)


def announce_memory_saved(fact_summary: str):
    """Speaks memory saved confirmation aloud."""
    SelectiveTTSEngine.speak_event(EVENT_MEMORY_SAVED, f"Saved memory: {fact_summary}")
