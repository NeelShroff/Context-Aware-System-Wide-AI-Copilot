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
EVENT_REMINDER_SET = "EVENT_REMINDER_SET"
EVENT_MUSIC_START = "EVENT_MUSIC_START"
EVENT_MEMORY_SAVED = "EVENT_MEMORY_SAVED"
EVENT_BUBBLE = "EVENT_BUBBLE"

ALLOWED_EVENT_CHANNELS = {
    EVENT_REMINDER,
    EVENT_REMINDER_SET,
    EVENT_MUSIC_START,
    EVENT_MEMORY_SAVED,
    EVENT_BUBBLE,
}

NOTIFICATION_SOUND_PATH = Path(__file__).resolve().parent.parent / "peter_parker_8bit.mp3"


def play_notification_chime():
    """Plays the 8-bit Peter Parker chime notification sound silently before reminders."""
    if NOTIFICATION_SOUND_PATH.exists():
        try:
            project_root = NOTIFICATION_SOUND_PATH.parent
            ffplay_exe = os.path.join(project_root, "ffplay_voice.exe")
            if not os.path.exists(ffplay_exe):
                ffplay_exe = os.path.join(project_root, "ffplay.exe")
            if not os.path.exists(ffplay_exe):
                ffplay_exe = shutil.which("ffplay") or "ffplay"

            cmd = [ffplay_exe, "-nodisp", "-autoexit", "-loglevel", "quiet", str(NOTIFICATION_SOUND_PATH)]
            subprocess.Popen(cmd, **get_no_window_kwargs())
        except Exception as e:
            logger.warning(f"Failed to play notification chime sound: {e}")



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


# Voice Presets Mapping (Supports names like 'spiderman', 'callum', 'sarah', etc.)
VOICE_PRESETS = {
    "spiderman": "N2lVS1w4EtoT3dr4eOWO",  # Callum - Husky, energetic, youthful hero voice
    "callum": "N2lVS1w4EtoT3dr4eOWO",
    "liam": "TX3LPaxmHKxFdv7VOQHJ",        # Liam - Energetic male voice
    "charlie": "IKne3meq5aSn9XLyUdCD",     # Charlie - Deep confident male voice
    "george": "JBFqnCBsd6RMkjVDRZzb",      # George - Warm storyteller male voice
    "sarah": "EXAVITQu4vr4xnSDxMaL",       # Sarah - Reassuring female voice
}


class SelectiveTTSEngine:
    """Singleton TTS Engine enforcing strict event channel filtering with ElevenLabs Flash v2.5 primary and pyttsx3 fallback."""

    _engine = None
    _lock = threading.Lock()
    _muted: bool = False
    _muted_initialized: bool = False
    _last_spoken_text: str = ""
    _last_spoken_time: float = 0.0

    @classmethod
    def is_muted(cls) -> bool:
        """Returns True if TTS voice announcements are muted."""
        if not cls._muted_initialized:
            env_val = os.getenv("TTS_MUTED", "false").strip().lower()
            cls._muted = env_val in ("true", "1", "yes")
            cls._muted_initialized = True
        return cls._muted

    @classmethod
    def set_muted(cls, muted: bool) -> bool:
        """Sets the mute state and updates TTS_MUTED in memory and environment."""
        with cls._lock:
            cls._muted = bool(muted)
            cls._muted_initialized = True
            os.environ["TTS_MUTED"] = "true" if cls._muted else "false"
            logger.info(f"SelectiveTTSEngine mute state set to: {cls._muted}")
            return cls._muted

    @classmethod
    def toggle_muted(cls) -> bool:
        """Toggles the current mute state."""
        return cls.set_muted(not cls.is_muted())

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
    def _speak_elevenlabs(cls, text: str, voice_override: str = None) -> bool:
        """
        Attempts to generate and play human-like voice audio using ElevenLabs Flash v2.5 API.
        Returns True if speech played successfully, False otherwise (triggering fallback).
        """
        api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        if not api_key or api_key == "your_elevenlabs_api_key_here":
            return False

        voice_input = (voice_override or os.getenv("ELEVENLABS_VOICE_ID", "spiderman")).strip()
        voice_id = VOICE_PRESETS.get(voice_input.lower(), voice_input)
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

            # Execute silent audio playback non-blockingly
            cmd = [ffplay_exe, "-nodisp", "-autoexit", "-loglevel", "quiet", tmp_path]
            proc = subprocess.Popen(cmd, **get_no_window_kwargs())

            # Cleanup temp file in background thread after playback finishes
            def _async_file_cleanup(process, file_path):
                try:
                    process.wait(timeout=25)
                except Exception:
                    pass
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass

            threading.Thread(target=_async_file_cleanup, args=(proc, tmp_path), daemon=True).start()

            logger.info("Successfully initiated ElevenLabs Flash v2.5 speech playback")
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
        Speaks text aloud ONLY if event_channel is in ALLOWED_EVENT_CHANNELS and TTS is not muted.
        Executes speech in a background thread to prevent blocking main execution.
        """
        if cls.is_muted():
            logger.info(f"TTS voice output is MUTED (suppressed event '{event_channel}')")
            return

        if event_channel not in ALLOWED_EVENT_CHANNELS:
            logger.info(f"TTS suppressed for non-allowed event channel '{event_channel}'")
            return

        if not text or not text.strip():
            return

        import time
        now = time.time()
        clean = text.strip()

        # Deduplicate rapid duplicate speech requests within 3.0 seconds
        if clean == cls._last_spoken_text and (now - cls._last_spoken_time) < 3.0:
            logger.info(f"Duplicate TTS speech suppressed within 3.0s: '{clean}'")
            return

        cls._last_spoken_text = clean
        cls._last_spoken_time = now

        def _speak_worker(speech_text: str, channel: str):
            with cls._lock:
                # Play 8-bit Peter Parker chime for reminder events before speaking
                if channel in (EVENT_REMINDER, EVENT_REMINDER_SET):
                    play_notification_chime()

                # Try ElevenLabs Flash v2.5 first
                success = cls._speak_elevenlabs(speech_text)
                if not success:
                    # Fallback to local pyttsx3
                    cls._speak_pyttsx3(speech_text)

        t = threading.Thread(target=_speak_worker, args=(clean, event_channel), daemon=True)
        t.start()



def detect_language(text: str) -> str:
    """
    Detects whether the text contains Hindi (Devanagari script) or follows Hindi config.
    Returns 'hi' for Hindi, 'en' for English.
    """
    if not text:
        return os.getenv("TTS_LANGUAGE", "hi").strip().lower()

    # Check for Devanagari script (\u0900 - \u097F)
    if any('\u0900' <= char <= '\u097F' for char in text):
        return "hi"

    config_lang = os.getenv("TTS_LANGUAGE", "auto").strip().lower()
    if config_lang in ("hi", "en"):
        return config_lang

    return "en"


def announce_reminder(reminder_text: str):
    """Speaks a reminder notification aloud in the user's interaction language (Hindi or English)."""
    lang = detect_language(reminder_text)
    if lang == "hi":
        msg = f"रिमाइंडर: {reminder_text}"
    else:
        msg = f"Reminder: {reminder_text}"
    SelectiveTTSEngine.speak_event(EVENT_REMINDER, msg)


def announce_reminder_set(reminder_text: str):
    """Speaks a reminder creation confirmation aloud when setting a reminder."""
    lang = detect_language(reminder_text)
    if lang == "hi":
        msg = f"रिमाइंडर सेट कर दिया गया है: {reminder_text}"
    else:
        msg = f"Reminder set: {reminder_text}"
    SelectiveTTSEngine.speak_event(EVENT_REMINDER_SET, msg)


def announce_music_start(track_name: str, artist: str = ""):
    """Speaks music start notification aloud in the user's interaction language (Hindi or English)."""
    combined_text = f"{track_name} {artist}"
    lang = detect_language(combined_text)
    if lang == "hi":
        msg = f"अब बज रहा है: {track_name}" if not artist else f"अब बज रहा है: {track_name}, कलाकार {artist}"
    else:
        msg = f"Now playing: {track_name}" if not artist else f"Now playing: {track_name} by {artist}"
    SelectiveTTSEngine.speak_event(EVENT_MUSIC_START, msg)


def announce_memory_saved(fact_summary: str):
    """Speaks memory saved confirmation aloud in the user's interaction language (Hindi or English)."""
    lang = detect_language(fact_summary)
    if lang == "hi":
        msg = f"जानकारी सेव हो गई है: {fact_summary}"
    else:
        msg = f"Saved memory: {fact_summary}"
    SelectiveTTSEngine.speak_event(EVENT_MEMORY_SAVED, msg)


def announce_speech_bubble(bubble_text: str):
    """Speaks general speech bubble text out loud, stripping UI emojis and suppressing error messages."""
    if not bubble_text:
        return
    import re
    # Suppress reading API error messages out loud
    text_lower = bubble_text.lower()
    error_keywords = ["unable to generate", "rate limit", "error 429", "error 400", "error 500", "api key not configured", "failed to connect", "http error"]
    if any(kw in text_lower for kw in error_keywords):
        logger.info(f"TTS suppressed for error message: '{bubble_text}'")
        return

    # Strip emojis and leading symbols
    clean_text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u27ff\u2300-\u23ff]', '', bubble_text).strip()
    if clean_text:
        SelectiveTTSEngine.speak_event(EVENT_BUBBLE, clean_text)



