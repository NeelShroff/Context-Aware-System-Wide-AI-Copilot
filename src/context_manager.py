import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class ContextManager:
    """
    Native Context Management Engine.
    Handles Project Workspace categories, priorities (HIGH, NORMAL, LOW),
    search index, and overlap/conflict resolution.
    """

    DEFAULT_STORE_PATH = Path("data/context_store.json")

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or self.DEFAULT_STORE_PATH
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load_store()

    def _load_store(self) -> Dict[str, Any]:
        if not self.store_path.exists():
            return {
                "active_workspace": "System-Wide AI Copilot",
                "workspaces": {
                    "System-Wide AI Copilot": {
                        "category": "Development",
                        "priority": "HIGH",
                        "description": "System-wide AI copilot project"
                    }
                }
            }
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"active_workspace": "System-Wide AI Copilot", "workspaces": {}}

    def _save_store(self):
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def set_active_workspace(self, name: str, category: str = "General", priority: str = "NORMAL") -> Dict[str, Any]:
        """Sets or creates active Project Workspace metadata."""
        workspaces = self.data.setdefault("workspaces", {})
        if name not in workspaces:
            workspaces[name] = {
                "category": category,
                "priority": priority,
                "description": f"{name} workspace"
            }
        self.data["active_workspace"] = name
        self._save_store()
        return workspaces[name]

    def update_workspace_metadata(self, name: str, category: Optional[str] = None, priority: Optional[str] = None) -> Dict[str, Any]:
        """Updates category and priority for a specific workspace."""
        workspaces = self.data.setdefault("workspaces", {})
        ws = workspaces.setdefault(name, {"category": "General", "priority": "NORMAL", "description": f"{name} workspace"})
        if category:
            ws["category"] = category
        if priority:
            ws["priority"] = priority.upper()
        self._save_store()
        return ws

    def get_workspace_metadata(self, name: str) -> Dict[str, Any]:
        """Returns metadata for a given workspace."""
        return self.data.get("workspaces", {}).get(name, {
            "category": "General",
            "priority": "NORMAL",
            "description": f"{name} workspace"
        })

    def search_workspaces(self, query: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Performs fuzzy query search over workspaces by name or category."""
        clean_q = query.strip().lower()
        results = []
        for name, meta in self.data.get("workspaces", {}).items():
            cat = meta.get("category", "").lower()
            if not clean_q or clean_q in name.lower() or clean_q in cat:
                results.append((name, meta))
        return results

    def delete_workspace(self, name: str) -> bool:
        """Deletes a workspace from memory store."""
        workspaces = self.data.get("workspaces", {})
        if name in workspaces:
            del workspaces[name]
            if self.data.get("active_workspace") == name:
                remaining = list(workspaces.keys())
                self.data["active_workspace"] = remaining[0] if remaining else "Default Project"
            self._save_store()
            return True
        return False
