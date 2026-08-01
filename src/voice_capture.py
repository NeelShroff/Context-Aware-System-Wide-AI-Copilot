"""
Voice Capture Module — Groq Whisper Transcription
Records microphone audio via sounddevice and transcribes using Groq whisper-large-v3-turbo.
"""
import io, json, os, urllib.request, urllib.error

try:
    import sounddevice as sd
    import numpy as np
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

from src.config import config

GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
WHISPER_MODEL = "whisper-large-v3-turbo"
SAMPLE_RATE = 16000
MAX_RECORD_SECONDS = 30


def _to_wav_bytes(frames, sample_rate: int) -> bytes:
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames.tobytes())
    return buf.getvalue()


def record_until_silence(max_seconds: float = MAX_RECORD_SECONDS, silence_threshold: float = 0.015, silence_gap: float = 1.5) -> bytes | None:
    """Record mic until silence for silence_gap seconds or max_seconds reached."""
    if not HAS_SOUNDDEVICE:
        return None
    chunk_size = int(SAMPLE_RATE * 0.1)
    all_frames = []
    silent_chunks = 0
    silence_chunks_needed = int(silence_gap / 0.1)
    max_chunks = int(max_seconds / 0.1)
    try:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=chunk_size)
        with stream:
            for _ in range(max_chunks):
                chunk, _ = stream.read(chunk_size)
                all_frames.append(chunk.copy())
                rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2))) / 32768.0
                if rms < silence_threshold:
                    silent_chunks += 1
                    if silent_chunks >= silence_chunks_needed and len(all_frames) > 10:
                        break
                else:
                    silent_chunks = 0
        if len(all_frames) < 3:
            return None
        audio_data = np.concatenate(all_frames, axis=0)
        return _to_wav_bytes(audio_data, SAMPLE_RATE)
    except Exception:
        return None


def transcribe_audio(wav_bytes: bytes) -> dict:
    """Send WAV bytes to Groq Whisper and return transcription result dict."""
    if not wav_bytes:
        return {"success": False, "text": "", "error": "No audio recorded."}
    api_key = getattr(config, "GROQ_API_KEY", None) or os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return {"success": False, "text": "", "error": "GROQ_API_KEY not set."}
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    b_head = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"model\"\r\n\r\n"
        f"{WHISPER_MODEL}\r\n"
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"response_format\"\r\n\r\n"
        f"json\r\n"
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"audio.wav\"\r\n"
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode("utf-8")
    b_tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = b_head + wav_bytes + b_tail

    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }
    try:
        req = urllib.request.Request(GROQ_WHISPER_URL, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "text": result.get("text", "").strip(), "error": None}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8") if e.fp else str(e)
        return {"success": False, "text": "", "error": f"HTTP {e.code}: {err[:120]}"}
    except Exception as e:
        return {"success": False, "text": "", "error": str(e)[:120]}


def dictate_to_text(max_seconds: float = 12.0) -> dict:
    """Record until silence and transcribe via Groq Whisper. Main entry point."""
    wav = record_until_silence(max_seconds=max_seconds)
    return transcribe_audio(wav)

