"""
Pet Bridge: HTTP Server & Context State Synchronization for 3D VRM Desktop Pet.
Exposes localhost endpoints for the WebGL overlay renderer to sync with Python context detector & LLM.
"""

import json
import logging
import os
import sys
import threading
import time
import ctypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# Add parent dir to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from src.context_detector import ContextDetector
except ImportError:
    ContextDetector = None

logger = logging.getLogger("PetBridge")
logger.setLevel(logging.INFO)

PET_CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "pet_config.json"))

def load_pet_config() -> dict:
    if os.path.exists(PET_CONFIG_FILE):
        try:
            with open(PET_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"character_style": "01 [Default]", "scale": 0.85}

def save_pet_config(config: dict):
    try:
        os.makedirs(os.path.dirname(PET_CONFIG_FILE), exist_ok=True)
        with open(PET_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save pet config: {e}")

_saved_cfg = load_pet_config()

# Global pet state shared across threads
PET_STATE = {
    "pet_mode": "IDLE",            # IDLE, THINKING, TALKING, CODING, CHAT, SLEEP
    "motion_state": "IDLE",        # IDLE, WALK, SPRINT, WEB_UP, WEB_DOWN, WEB_DIAGONAL, LAND, SLEEP
    "heading_dir": 1,              # 1 = Facing Right, -1 = Facing Left
    "move_angle": 0,               # Trajectory angle in degrees
    "vector_x": 0.0,               # Normalized direction X
    "vector_y": 0.0,               # Normalized direction Y
    "web_anchor_x": None,          # Relative canvas X for web anchor
    "web_anchor_y": None,          # Relative canvas Y for web anchor
    "char_rel_x": None,            # Relative canvas X for character sprite (None = default centerX)
    "char_rel_y": None,            # Relative canvas Y for character sprite (None = default centerY)
    "web_shoot_trigger": False,    # True when launching interactive web shoot across screen
    "is_moving": False,
    "active_app": "Desktop",
    "domain_category": "GENERAL",
    "is_coding_env": False,
    "is_chat_env": False,
    "speech_text": "✨ Your friendly neighborhood Spider-Man is ready!",
    "speech_timestamp": time.time(),
    "speech_duration": 6.0,
    "mood_expression": "happy",      # happy, thinking, aa, blink, surprised
    "character_style": _saved_cfg.get("character_style", "01 [Default]"),
    "scale": _saved_cfg.get("scale", 0.85)
}

_state_lock = threading.Lock()

def update_pet_state(updates: dict):
    with _state_lock:
        PET_STATE.update(updates)
        if "character_style" in updates or "scale" in updates:
            save_pet_config({
                "character_style": PET_STATE.get("character_style", "01 [Default]"),
                "scale": PET_STATE.get("scale", 0.85)
            })

def get_pet_state() -> dict:
    with _state_lock:
        return dict(PET_STATE)

def get_active_window_context() -> dict:
    """Uses native Windows ctypes & psutil API to get foreground window title & process name."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or "Desktop"
        
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        proc_name = "explorer.exe"
        try:
            import psutil
            if pid.value > 0:
                proc_name = psutil.Process(pid.value).name().lower()
        except Exception:
            pass

        return {
            "title": title,
            "process": proc_name,
            "hwnd": hwnd
        }
    except Exception:
        return {"title": "Desktop", "process": "explorer.exe"}

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP Server for non-blocking API handling."""
    daemon_threads = True

class PetBridgeRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy HTTP GET logging in console
        pass

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        if self.path.startswith("/api/status"):
            state = get_pet_state()
            self._set_headers(200)
            self.wfile.write(json.dumps(state).encode("utf-8"))
        elif self.path.startswith("/api/character"):
            import urllib.parse
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            style = query.get("style", ["01 [Default]"])[0]
            update_pet_state({"character_style": style})
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "character_updated", "style": style}).encode("utf-8"))
        elif self.path.startswith("/api/pause_wander"):
            update_pet_state({"pause_wander": True, "pause_timestamp": time.time()})
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "wandering_paused"}).encode("utf-8"))
        elif self.path.startswith("/api/open_url"):
            import urllib.parse, webbrowser
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            target_url = query.get("url", ["http://127.0.0.1:8000"])[0]
            webbrowser.open(target_url)
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "url_opened", "url": target_url}).encode("utf-8"))

        elif self.path.startswith("/api/chat/open"):
            update_pet_state({"open_chat_window": True, "chat_ts": time.time()})
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "chat_window_opened"}).encode("utf-8"))
        elif self.path.startswith("/api/expand_window"):
            import urllib.parse
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            expand = query.get("expand", ["true"])[0].lower() == "true"
            update_pet_state({"window_expand": expand, "expand_timestamp": time.time()})
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "window_expand", "expand": expand}).encode("utf-8"))
        elif self.path.startswith("/api/health"):
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "ok", "uptime": time.time()}).encode("utf-8"))
        elif self.path.startswith("/sprite/"):
            import urllib.parse
            rel_path = urllib.parse.unquote(self.path[len("/sprite/"):])
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "PC _ Computer - Marvel Cosmic Invasion - Playable Characters - Spider-Man", "Marvel Cosmic Invasion", "Spider-Man"))
            file_path = os.path.abspath(os.path.join(base_dir, rel_path))
            if file_path.lower().startswith(base_dir.lower()) and os.path.exists(file_path) and os.path.isfile(file_path):
                self._set_headers(200, "image/png")
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Sprite file not found"}).encode("utf-8"))
        elif self.path.startswith("/sprite_root/"):
            import urllib.parse
            filename = urllib.parse.unquote(self.path[len("/sprite_root/"):])
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "PC _ Computer - Marvel Cosmic Invasion - Playable Characters - Spider-Man", "Marvel Cosmic Invasion", "Spider-Man"))
            file_path = os.path.abspath(os.path.join(base_dir, filename))
            if file_path.lower().startswith(base_dir.lower()) and os.path.exists(file_path) and os.path.isfile(file_path):
                self._set_headers(200, "image/png")
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Root sprite not found"}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))


    def do_POST(self):
        if self.path.startswith("/api/update"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                update_pet_state(data)
                self._set_headers(200)
                self.wfile.write(json.dumps({"status": "updated", "state": get_pet_state()}).encode("utf-8"))
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        elif self.path.startswith("/api/speech"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                text = data.get("text", "")
                duration = float(data.get("duration", 6.0))
                mode = data.get("mode", "TALKING")
                update_pet_state({
                    "speech_text": text,
                    "speech_duration": duration,
                    "speech_timestamp": time.time(),
                    "pet_mode": mode,
                    "mood_expression": "aa" if mode == "TALKING" else "thinking"
                })
                self._set_headers(200)
                self.wfile.write(json.dumps({"status": "speech_posted"}).encode("utf-8"))
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        elif self.path.startswith("/api/copilot"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                update_pet_state({
                    "speech_text": "✨ Processing Copilot Query...",
                    "speech_duration": 4.0,
                    "speech_timestamp": time.time(),
                    "pet_mode": "THINKING",
                    "mood_expression": "thinking"
                })
                from src.main import process_request
                result = process_request(data)
                if result.get("success"):
                    scenario_desc = result.get("scenario_description", "Completed")
                    update_pet_state({
                        "speech_text": f"✅ Done! ({scenario_desc})",
                        "speech_duration": 3.0,
                        "speech_timestamp": time.time(),
                        "pet_mode": "TALKING",
                        "mood_expression": "aa"
                    })
                else:
                    err_msg = result.get("error", "Error")
                    update_pet_state({
                        "speech_text": f"❌ {err_msg}",
                        "speech_duration": 3.0,
                        "speech_timestamp": time.time(),
                        "pet_mode": "IDLE",
                        "mood_expression": "blink"
                    })
                self._set_headers(200)
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                logger.error(f"Error executing /api/copilot: {e}", exc_info=True)
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
        elif self.path.startswith("/api/chat/unified"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                msg = data.get("message", "")
                ctx = data.get("context", {})
                from src.chat_engine import AutonomousChatEngine
                res = AutonomousChatEngine.process_unified_chat(msg, ctx)
                self._set_headers(200)
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                logger.error(f"Error executing /api/chat/unified: {e}", exc_info=True)
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "reply": f"Error: {str(e)}"}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))


class ContextMonitorThread(threading.Thread):
    """Background thread polling window context and updating pet state."""
    def __init__(self, poll_interval=1.5):
        super().__init__(daemon=True)
        self.poll_interval = poll_interval

    def _get_idle_seconds(self) -> float:
        try:
            import ctypes
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]
            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo)):
                millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
                return millis / 1000.0
        except Exception:
            pass
        return 0.0

    def run(self):
        logger.info("Context Monitor Thread started.")
        while True:
            try:
                ctx = get_active_window_context()
                title = ctx.get("title", "Desktop")
                
                scenario_code = "GENERAL"
                scenario_desc = "General Workspace"
                
                if ContextDetector:
                    scenario_code, scenario_desc = ContextDetector.detect_scenario(ctx)

                proc = ctx.get("process", "").lower()
                title_lower = title.lower()

                is_coding = (
                    "code.exe" in proc or "devenv.exe" in proc or "pycharm" in proc or "idea64" in proc or
                    "SOURCE_CODE" in scenario_code or "TECHNICAL" in scenario_code or "AI_PROMPT" in scenario_code or
                    "code" in title_lower or "visual studio" in title_lower
                )

                is_chat = (
                    "chrome.exe" in proc or "msedge.exe" in proc or "firefox.exe" in proc or "brave.exe" in proc or "opera.exe" in proc or
                    "CHAT" in scenario_code or "EMAIL" in scenario_code or "chrome" in title_lower or "edge" in title_lower or "youtube" in title_lower
                )

                current_mode = get_pet_state().get("pet_mode", "IDLE")

                # CPU Monitoring for Spider-Sense Alert
                cpu_load = 0
                try:
                    import psutil
                    cpu_load = psutil.cpu_percent(interval=None)
                except Exception:
                    pass

                idle_sec = self._get_idle_seconds()

                new_updates = {
                    "active_app": title,
                    "domain_category": scenario_code,
                    "is_coding_env": is_coding,
                    "is_chat_env": is_chat,
                    "cpu_load": cpu_load,
                    "idle_seconds": idle_sec
                }

                if cpu_load > 80:
                    new_updates["pet_mode"] = "THINKING"
                    new_updates["speech_text"] = "⚡ Spider-Sense is tingling! System CPU load high!"
                    new_updates["speech_duration"] = 4.0
                    new_updates["speech_timestamp"] = time.time()
                elif idle_sec >= 120:
                    new_updates["pet_mode"] = "SLEEP"
                    new_updates["motion_state"] = "SLEEP"
                    new_updates["speech_text"] = "Zzz... Web-sleeping..."
                    new_updates["speech_duration"] = 5.0
                    new_updates["speech_timestamp"] = time.time()
                elif current_mode == "SLEEP" and idle_sec < 3:
                    new_updates["pet_mode"] = "IDLE"
                    new_updates["motion_state"] = "IDLE"
                elif current_mode not in ("THINKING", "TALKING", "SLEEP"):
                    if is_coding:
                        new_updates["pet_mode"] = "CODING"
                        new_updates["mood_expression"] = "focused"
                    elif is_chat:
                        new_updates["pet_mode"] = "CHAT"
                        new_updates["mood_expression"] = "happy"
                    else:
                        new_updates["pet_mode"] = "IDLE"
                        new_updates["mood_expression"] = "happy"

                update_pet_state(new_updates)

            except Exception as e:
                logger.error(f"Error polling context: {e}")

            time.sleep(self.poll_interval)


def start_pet_server(host="127.0.0.1", port=8799):
    server = ThreadedHTTPServer((host, port), PetBridgeRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    logger.info(f"Pet Bridge Server started at http://{host}:{port}")

    # Start Context Monitor
    monitor = ContextMonitorThread()
    monitor.start()

    return server

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Starting Pet Bridge Server test on http://127.0.0.1:8765...")
    srv = start_pet_server()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server stopped.")
