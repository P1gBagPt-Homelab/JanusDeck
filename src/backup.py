"""JanusDeck Automated Backup Inspection and Management Service.

Provides real-time inspection of local backup archives, validation of whether
today's automated backup was completed, and manual backup triggers.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from src.config import AppConfig, get_config

logger = logging.getLogger("janus.backup")


def format_size(size_bytes: int) -> str:
    """Format bytes into a human-readable string (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class BackupItem:
    """Represents a single snapshot archive file and its parsed metadata."""

    def __init__(self, path: Path):
        self.path = path
        self.filename = path.name
        self.stat = path.stat()
        self.size_bytes = self.stat.st_size
        self.size_formatted = format_size(self.size_bytes)
        self.mtime = self.stat.st_mtime

        mtime_dt = datetime.fromtimestamp(self.mtime)
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")

        # Extract YYYY-MM-DD and optional HH-MM-SS or HHMMSS from filename
        # Examples: janus_backup_2026-11-08_03-00-01.tar.gz, janus_backup_2026-11-08_030000.tar.gz
        date_pattern = r"(\d{4}-\d{2}-\d{2})(?:[_-](\d{2})[-:]?(\d{2})[-:]?(\d{2}))?"
        match = re.search(date_pattern, self.filename)

        if match:
            date_str = match.group(1)
            self.date_str = date_str
            if match.group(2) and match.group(3) and match.group(4):
                time_str = f"{match.group(2)}:{match.group(3)}:{match.group(4)}"
            else:
                time_str = "03:00:00"

            try:
                dt_obj = datetime.fromisoformat(f"{date_str}T{time_str}")
                self.created_at = dt_obj.isoformat()
                self.timestamp = dt_obj.timestamp()
            except ValueError:
                self.created_at = mtime_dt.isoformat()
                self.timestamp = self.mtime

            # Explicit date in filename takes precedence
            self.is_today = (self.date_str == today_str)
        else:
            self.date_str = mtime_dt.strftime("%Y-%m-%d")
            self.created_at = mtime_dt.isoformat()
            self.timestamp = self.mtime
            self.is_today = (mtime_dt.date() == today)

        # Calculate relative age in days
        try:
            parsed_date = datetime.strptime(self.date_str, "%Y-%m-%d").date()
            diff = (today - parsed_date).days
            self.age_days = max(0, diff)
        except Exception:
            self.age_days = max(0, (today - mtime_dt.date()).days)

        if self.age_days == 0:
            self.relative_time = "Today"
        elif self.age_days == 1:
            self.relative_time = "Yesterday"
        else:
            self.relative_time = f"{self.age_days} days ago"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "size_formatted": self.size_formatted,
            "created_at": self.created_at,
            "date": self.date_str,
            "is_today": self.is_today,
            "age_days": self.age_days,
            "relative_time": self.relative_time,
        }


class BackupManager:
    """Manages backup inspection, status aggregation, and manual trigger requests."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()

    def get_backup_dir(self) -> Path:
        return Path(self.config.backup.backup_dir)

    def get_status(self) -> Dict[str, Any]:
        """Inspects the local backup directory and checks whether today's backup exists."""
        backup_dir = self.get_backup_dir()
        today_str = date.today().strftime("%Y-%m-%d")
        rclone_remote = self.config.backup.rclone_remote

        if not backup_dir.is_dir():
            return {
                "backup_dir": str(backup_dir),
                "directory_exists": False,
                "today_done": False,
                "today_date": today_str,
                "today_backup": None,
                "latest_backup": None,
                "total_backups": 0,
                "total_size_bytes": 0,
                "total_size_formatted": "0 B",
                "backups": [],
                "rclone_remote": rclone_remote,
                "retention_days_local": self.config.backup.retention_days_local,
                "retention_days_cloud": self.config.backup.retention_days_cloud,
                "message": f"Backup directory '{backup_dir}' not found on host.",
            }

        # Gather all backup snapshot files
        items: List[BackupItem] = []
        try:
            for entry in backup_dir.iterdir():
                if entry.is_file() and (
                    entry.name.endswith(".tar.gz")
                    or entry.name.endswith(".tgz")
                    or entry.name.endswith(".tar")
                    or entry.name.endswith(".sql")
                ):
                    try:
                        items.append(BackupItem(entry))
                    except Exception as exc:
                        logger.warning("Could not read backup file '%s': %s", entry, exc)
        except Exception as exc:
            logger.error("Failed to list files in backup directory '%s': %s", backup_dir, exc)

        # Sort archives newest to oldest
        items.sort(key=lambda b: b.timestamp, reverse=True)

        today_backups = [b for b in items if b.is_today]
        today_done = len(today_backups) > 0
        today_backup = today_backups[0].to_dict() if today_done else None
        latest_backup = items[0].to_dict() if items else None
        total_size = sum(b.size_bytes for b in items)

        return {
            "backup_dir": str(backup_dir),
            "directory_exists": True,
            "today_done": today_done,
            "today_date": today_str,
            "today_backup": today_backup,
            "latest_backup": latest_backup,
            "total_backups": len(items),
            "total_size_bytes": total_size,
            "total_size_formatted": format_size(total_size),
            "backups": [b.to_dict() for b in items],
            "rclone_remote": rclone_remote,
            "retention_days_local": self.config.backup.retention_days_local,
            "retention_days_cloud": self.config.backup.retention_days_cloud,
        }

    async def trigger_backup(self, force: bool = False) -> Dict[str, Any]:
        """Triggers the backup script (/data/scripts/backup-janus.sh) asynchronously."""
        script_path = Path(self.config.backup.backup_script)
        if not script_path.is_file():
            logger.warning("Backup script not found at %s", script_path)
            return {
                "success": False,
                "status": "error",
                "message": f"Backup execution script not found at {script_path}",
            }

        cmd = ["bash", str(script_path)]
        if force:
            cmd.append("--force")

        logger.info("Executing automated backup script: %s", " ".join(cmd))
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            success = proc.returncode == 0
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if not success:
                logger.error("Backup script failed with exit code %s: %s", proc.returncode, stderr_str)
                return {
                    "success": False,
                    "status": "failed",
                    "returncode": proc.returncode,
                    "message": f"Backup script failed (exit code {proc.returncode}): {stderr_str or stdout_str}",
                }

            logger.info("Automated backup script completed successfully.")
            return {
                "success": True,
                "status": "completed",
                "message": "Automated backup executed successfully.",
                "output": stdout_str,
            }
        except Exception as exc:
            logger.error("Unexpected error executing backup script: %s", exc)
            return {
                "success": False,
                "status": "error",
                "message": f"Execution error: {str(exc)}",
            }


_backup_manager: Optional[BackupManager] = None


def get_backup_manager(config: Optional[AppConfig] = None) -> BackupManager:
    """Retrieves or creates the singleton BackupManager instance."""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager(config)
    return _backup_manager
