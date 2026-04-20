import json
import os
import threading
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()


class SnapStore:
    """Simple JSON file-backed snapshot store with bounded retention."""

    def __init__(self, path: str, max_snaps: int = 500) -> None:
        self.path = path
        self.max_snaps = max(1, int(max_snaps or 1))
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump({"snaps": []}, f)

    def _load(self) -> Dict[str, Any]:
        with open(self.path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except Exception:
                return {"snaps": []}

    def _save(self, data: Dict[str, Any]) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    def add(self, snap: Dict[str, Any]) -> None:
        with _LOCK:
            data = self._load()
            snaps: List[Dict[str, Any]] = data.get("snaps", [])
            snaps.append(snap)
            if len(snaps) > self.max_snaps:
                snaps = snaps[-self.max_snaps :]
            data["snaps"] = snaps
            self._save(data)

    def list(self) -> List[Dict[str, Any]]:
        with _LOCK:
            return list(self._load().get("snaps", []))

    def get(self, snap_id: str) -> Optional[Dict[str, Any]]:
        with _LOCK:
            for s in self._load().get("snaps", []):
                if s.get("id") == snap_id:
                    return s
            return None

    def delete(self, snap_id: str) -> bool:
        with _LOCK:
            data = self._load()
            snaps = data.get("snaps", [])
            new_snaps = [s for s in snaps if s.get("id") != snap_id]
            if len(new_snaps) == len(snaps):
                return False
            data["snaps"] = new_snaps
            self._save(data)
            return True
