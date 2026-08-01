import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class HistoryManager:
    """
    Manages application-separated history records and Time-Aware Chronological Activity Timelines.
    Stores entries in data/history/<process_name>.json
    Maintains an index in data/history/index.json
    """

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "data"
        
        self.history_dir = data_dir / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.history_dir / "index.json"
        self._init_index()

    def _init_index(self):
        if not self.index_file.exists():
            self._write_json(self.index_file, {
                "total_entries": 0,
                "applications": {},
                "last_updated": datetime.now().isoformat()
            })

    def _read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_json(self, path: Path, data: Any):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _sanitize_filename(self, process_name: str) -> str:
        safe_name = "".join(c for c in process_name if c.isalnum() or c in (" ", "_", "-", "."))
        return safe_name or "general.exe"

    def record_entry(
        self,
        process_name: str,
        title: str,
        scenario: str,
        original_text: str,
        rewritten_text: str,
        entities: List[str] = None
    ) -> Dict[str, Any]:
        """
        Appends a new rewrite event to the application's history log.
        """
        if entities is None:
            entities = []

        safe_proc = self._sanitize_filename(process_name)
        app_file = self.history_dir / f"{safe_proc}.json"

        app_data = self._read_json(app_file)
        if "entries" not in app_data:
            app_data = {
                "process": process_name,
                "total_count": 0,
                "entries": []
            }

        entry_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        entry = {
            "id": entry_id,
            "timestamp": timestamp,
            "title": title,
            "scenario": scenario,
            "original_text": original_text,
            "rewritten_text": rewritten_text,
            "entities": entities
        }

        app_data["entries"].append(entry)
        app_data["total_count"] = len(app_data["entries"])
        self._write_json(app_file, app_data)

        # Update index
        index = self._read_json(self.index_file)
        index["total_entries"] = index.get("total_entries", 0) + 1
        apps = index.get("applications", {})
        apps[process_name] = {
            "count": app_data["total_count"],
            "last_interaction": timestamp,
            "last_scenario": scenario
        }
        index["applications"] = apps
        index["last_updated"] = timestamp
        self._write_json(self.index_file, index)

        return entry

    def get_app_history(self, process_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves the most recent entries for a specific application.
        """
        safe_proc = self._sanitize_filename(process_name)
        app_file = self.history_dir / f"{safe_proc}.json"

        app_data = self._read_json(app_file)
        entries = app_data.get("entries", [])
        return entries[-limit:]

    def get_recent_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves recent entries across all applications sorted by timestamp.
        """
        all_entries = []
        for p in self.history_dir.glob("*.json"):
            if p.name == "index.json":
                continue
            data = self._read_json(p)
            for entry in data.get("entries", []):
                entry_copy = dict(entry)
                entry_copy["process"] = data.get("process", p.stem)
                all_entries.append(entry_copy)

        all_entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_entries[:limit]

    def get_chronological_timeline(self, limit: int = 5) -> List[str]:
        """
        Generates a human-readable timestamped chronological activity timeline.
        Formats: '[12:35 PM - 5m ago in WhatsApp (Chat with Mohil)] User wrote: "..." -> AI: "..."'
        """
        recent = self.get_recent_history(limit=limit)
        timeline = []
        now = datetime.now()

        for entry in reversed(recent):
            ts_str = entry.get("timestamp", "")
            time_label = ""
            if ts_str:
                try:
                    dt = datetime.fromisoformat(ts_str)
                    delta_sec = int((now - dt).total_seconds())
                    time_str = dt.strftime("%I:%M %p").lstrip("0")
                    if delta_sec < 60:
                        ago = "just now"
                    elif delta_sec < 3600:
                        ago = f"{delta_sec // 60}m ago"
                    else:
                        ago = f"{delta_sec // 3600}h ago"
                    time_label = f"[{time_str} - {ago}] "
                except Exception:
                    time_label = ""

            proc = entry.get("process", "app")
            title = entry.get("title", "")
            orig = entry.get("original_text", "")
            rew = entry.get("rewritten_text", "")

            # Truncate text snippets cleanly
            orig_snippet = orig[:80].replace("\n", " ") + ("..." if len(orig) > 80 else "")
            rew_snippet = rew[:80].replace("\n", " ") + ("..." if len(rew) > 80 else "")

            title_info = f" ({title})" if title and title != "Unknown" else ""
            line = f"{time_label}In {proc}{title_info}: User wrote: \"{orig_snippet}\" -> AI Output: \"{rew_snippet}\""
            timeline.append(line)

        return timeline
