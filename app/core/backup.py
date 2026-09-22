"""Automated Backup and Archive Utility for SQLite/Postgres DBs, Journals, and Configs."""

import os
import shutil
import tarfile
from datetime import datetime, timezone
from typing import List, Optional


class ProductionBackupManager:
    """Creates compressed timestamped archives of trade logs, configs, and analytical databases."""

    def __init__(
        self,
        backup_dir: str = "data/backups",
        source_dirs: Optional[List[str]] = None,
        source_files: Optional[List[str]] = None
    ) -> None:
        self.backup_dir = backup_dir
        self.source_dirs = source_dirs or ["data/paper_trading", "data/research", "configs"]
        self.source_files = source_files or [".env.example"]

    def create_snapshot_backup(self) -> str:
        """Create a compressed .tar.gz archive containing journals and configs."""
        os.makedirs(self.backup_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_name = f"fox_backup_{timestamp}.tar.gz"
        archive_path = os.path.join(self.backup_dir, archive_name)

        with tarfile.open(archive_path, "w:gz") as tar:
            for s_dir in self.source_dirs:
                if os.path.exists(s_dir):
                    tar.add(s_dir, arcname=os.path.basename(s_dir))

            for s_file in self.source_files:
                if os.path.exists(s_file):
                    tar.add(s_file, arcname=os.path.basename(s_file))

        return archive_path

    def prune_old_backups(self, retention_count: int = 14) -> List[str]:
        """Delete older backup archives exceeding the retention threshold."""
        if not os.path.exists(self.backup_dir):
            return []

        backups = sorted([
            os.path.join(self.backup_dir, f)
            for f in os.listdir(self.backup_dir)
            if f.startswith("fox_backup_") and f.endswith(".tar.gz")
        ], key=os.path.getmtime, reverse=True)

        removed: List[str] = []
        if len(backups) > retention_count:
            for old_b in backups[retention_count:]:
                try:
                    os.remove(old_b)
                    removed.append(old_b)
                except Exception:
                    pass

        return removed
