"""
Version Management & Audit Tracking for Generated Artifacts
Stores snapshot histories, unified text diffs, and rollback checkpoints.
"""
import os
import shutil
import time
from typing import List, Dict, Any, Optional
from core.models import VersionRecord

class VersionManager:
    def __init__(self, versions_dir: str = "versions"):
        self.versions_dir = versions_dir
        os.makedirs(self.versions_dir, exist_ok=True)
        self.history: List[VersionRecord] = []

    def snapshot(self, version: str, instruction: str, doc_path: Optional[str] = None,
                 ppt_path: Optional[str] = None, author: str = "User Conversational Edit",
                 diffs: Optional[List[str]] = None) -> VersionRecord:
        """Captures a timestamped copy of the active artifacts."""
        v_folder = os.path.join(self.versions_dir, version)
        os.makedirs(v_folder, exist_ok=True)

        saved_doc = None
        saved_ppt = None

        if doc_path and os.path.exists(doc_path):
            dst = os.path.join(v_folder, os.path.basename(doc_path))
            shutil.copy2(doc_path, dst)
            saved_doc = dst

        if ppt_path and os.path.exists(ppt_path):
            dst = os.path.join(v_folder, os.path.basename(ppt_path))
            shutil.copy2(ppt_path, dst)
            saved_ppt = dst

        record = VersionRecord(
            version=version,
            timestamp=time.time(),
            author=author,
            instruction=instruction,
            doc_path=saved_doc,
            ppt_path=saved_ppt,
            diff_summary=diffs or [f"Applied modification: {instruction}"],
            changes_count=len(diffs) if diffs else 1
        )
        self.history.append(record)
        return record

    def get_history(self) -> List[Dict[str, Any]]:
        return [
            {
                "version": r.version,
                "timestamp": r.timestamp,
                "author": r.author,
                "instruction": r.instruction,
                "diff_summary": r.diff_summary,
                "doc_path": r.doc_path,
                "ppt_path": r.ppt_path,
                "changes_count": r.changes_count
            }
            for r in self.history
        ]
