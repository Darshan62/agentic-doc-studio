"""
Version Manager
Copies the generated files into versions/<version>/ after every generation or edit,
and keeps the history in versions/history.json so it survives between requests.
"""
import json
import os
import shutil
import time
from typing import Any, Dict, List


class VersionManager:
    def __init__(self, versions_dir: str = "versions"):
        self.versions_dir = versions_dir
        self.history_file = os.path.join(versions_dir, "history.json")
        os.makedirs(versions_dir, exist_ok=True)
        self.history: List[Dict[str, Any]] = []
        if os.path.exists(self.history_file):
            with open(self.history_file, encoding="utf-8") as f:
                self.history = json.load(f)

    def next_version(self) -> str:
        """v1.0 for the first generation, then v1.1, v1.2 ... for each edit."""
        return f"v1.{len(self.history)}" if self.history else "v1.0"

    def reset(self) -> None:
        self.history = []

    def snapshot(self, instruction: str, doc_path: str, ppt_path: str,
                 author: str, changes: List[str]) -> Dict[str, Any]:
        version = self.next_version()
        folder = os.path.join(self.versions_dir, version)
        os.makedirs(folder, exist_ok=True)
        saved_doc = shutil.copy2(doc_path, folder)
        saved_ppt = shutil.copy2(ppt_path, folder)

        record = {
            "version": version,
            "timestamp": time.time(),
            "author": author,
            "instruction": instruction,
            "diff_summary": changes,
            "doc_path": saved_doc,
            "ppt_path": saved_ppt,
            "changes_count": len(changes),
        }
        self.history.append(record)
        self._save()
        return record

    def snapshot_file(self, instruction: str, file_path: str, author: str, changes: List[str]) -> Dict[str, Any]:
        """Single-file variant used by the editor workspace (one artifact per history)."""
        version = self.next_version()
        folder = os.path.join(self.versions_dir, version)
        os.makedirs(folder, exist_ok=True)
        record = {
            "version": version,
            "timestamp": time.time(),
            "author": author,
            "instruction": instruction,
            "diff_summary": changes,
            "file_path": shutil.copy2(file_path, folder),
            "changes_count": len(changes),
        }
        self.history.append(record)
        self._save()
        return record

    def truncate(self, keep: int) -> None:
        """Drops the versions after the first `keep` (an edit after undo discards the redo branch)."""
        self.history = self.history[:keep]
        self._save()

    def _save(self) -> None:
        # Write-then-rename, so a crash mid-write can't leave a truncated history.json
        tmp = self.history_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)
        os.replace(tmp, self.history_file)

    def get_history(self) -> List[Dict[str, Any]]:
        return self.history
