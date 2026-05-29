"""Persist last-known stock state to avoid duplicate Telegram alerts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"skus": {}}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"skus": {}}

    def save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def was_available(self, sku: str) -> bool | None:
        entry = self._data.get("skus", {}).get(sku)
        if entry is None:
            return None
        return bool(entry.get("available"))

    def update(self, sku: str, *, available: bool, message: str) -> None:
        self._data.setdefault("skus", {})[sku] = {
            "available": available,
            "message": message,
        }
