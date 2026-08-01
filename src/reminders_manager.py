"""
Reminders Manager Module.
Parses natural language timer/reminder requests, sets background scheduling threads,
and emits 3D Pet speech bubbles + spoken TTS announcements when reminders fire.
"""
import os
import re
import sys
import json
import time
import sqlite3
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("RemindersManager")
logger.setLevel(logging.INFO)

from src.tts_engine import announce_reminder

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "reminders.db"


class RemindersManager:
    """Manages timer-backed reminders and spoken event alerts."""

    def __init__(self):
        os.makedirs(DB_PATH.parent, exist_ok=True)
        self._init_db()
        self._active_timers: Dict[int, threading.Timer] = {}

    def _init_db(self):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text TEXT NOT NULL,
                        trigger_timestamp REAL NOT NULL,
                        created_timestamp REAL NOT NULL,
                        status TEXT DEFAULT 'PENDING'
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize reminders DB: {e}")

    @staticmethod
    def parse_delay_seconds(query: str) -> Optional[float]:
        """Extracts delay in seconds from natural language strings like 'in 5 minutes', 'in 30 seconds', 'in 1 hour'."""
        query_lower = query.lower()

        sec_match = re.search(r'in\s+(\d+)\s*(sec|second)', query_lower)
        if sec_match:
            return float(sec_match.group(1))

        min_match = re.search(r'in\s+(\d+)\s*(min|minute)', query_lower)
        if min_match:
            return float(min_match.group(1)) * 60.0

        hr_match = re.search(r'in\s+(\d+)\s*(hr|hour)', query_lower)
        if hr_match:
            return float(hr_match.group(1)) * 3600.0

        # Default fallback if 'remind me to X' without explicit time is given: 5 minutes
        if "remind" in query_lower:
            return 300.0

        return None

    def add_reminder(self, reminder_text: str, delay_seconds: float) -> Dict[str, Any]:
        """Schedules a new timer-backed reminder."""
        now = time.time()
        trigger_time = now + max(delay_seconds, 1.0)

        reminder_id = -1
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO reminders (text, trigger_timestamp, created_timestamp, status) VALUES (?, ?, ?, 'PENDING')",
                    (reminder_text, trigger_time, now)
                )
                reminder_id = cursor.lastrowid
                conn.commit()
        except Exception as e:
            logger.error(f"Error inserting reminder to DB: {e}")

        def _fire_reminder():
            logger.info(f"Firing reminder #{reminder_id}: '{reminder_text}'")

            # Update DB status
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute("UPDATE reminders SET status = 'FIRED' WHERE id = ?", (reminder_id,))
                    conn.commit()
            except Exception:
                pass

            # 1. Announce reminder via selective TTS channel
            announce_reminder(reminder_text)

            # 2. Update 3D Pet speech bubble
            try:
                import urllib.request
                speech_payload = json.dumps({
                    "text": f"⏰ Reminder: {reminder_text}",
                    "duration": 7.0,
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

        timer = threading.Timer(delay_seconds, _fire_reminder)
        timer.daemon = True
        timer.start()

        if reminder_id > 0:
            self._active_timers[reminder_id] = timer

        mins = round(delay_seconds / 60.0, 1)
        time_str = f"{delay_seconds:.0f} seconds" if delay_seconds < 60 else f"{mins} minutes"

        return {
            "success": True,
            "reminder_id": reminder_id,
            "text": reminder_text,
            "delay_seconds": delay_seconds,
            "message": f"Reminder set for {time_str}: '{reminder_text}'"
        }
