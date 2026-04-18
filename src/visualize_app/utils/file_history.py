"""
File history manager for tracking recently opened files.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List

from visualize_app.utils.setup_config import get_app_data_dir


class FileHistory:
    """Manages history of recently opened files."""

    def __init__(self, max_items: int = 10):
        self.max_items = max_items
        self.history_file = get_app_data_dir() / "history.json"
        self._history: List[dict] = []
        self._load()

    def _load(self):
        """Load history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
            except Exception:
                self._history = []
        else:
            self._history = []

    def _save(self):
        """Save history to file."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, file_path: str):
        """Add file to history."""
        file_path = str(Path(file_path).absolute())

        # Remove if already exists
        self._history = [item for item in self._history if item.get("path") != file_path]

        # Add to beginning
        self._history.insert(
            0,
            {
                "path": file_path,
                "name": Path(file_path).name,
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Keep only max_items
        self._history = self._history[: self.max_items]

        self._save()

    def get_recent(self, limit: int | None = None) -> List[dict]:
        """Get recent files."""
        if limit is None:
            limit = self.max_items

        # Filter out non-existing files
        valid_history = []
        for item in self._history:
            if Path(item["path"]).exists():
                valid_history.append(item)

        # Update if some files were removed
        if len(valid_history) != len(self._history):
            self._history = valid_history
            self._save()

        return self._history[:limit]

    def clear(self):
        """Clear all history."""
        self._history = []
        self._save()
