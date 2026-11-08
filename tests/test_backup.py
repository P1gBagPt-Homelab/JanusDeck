from datetime import date, timedelta
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient

from src.backup import BackupItem, BackupManager, format_size
from src.config import AppConfig, BackupConfig, SecurityConfig
from src.main import app


def test_format_size():
    assert format_size(500) == "500 B"
    assert format_size(1024) == "1.0 KB"
    assert format_size(1024 * 1024 * 50) == "50.0 MB"
    assert format_size(1024 * 1024 * 1024 * 2) == "2.00 GB"


def test_backup_nonexistent_directory(tmp_path):
    missing_dir = tmp_path / "does_not_exist"
    cfg = AppConfig(backup=BackupConfig(backup_dir=str(missing_dir)))
    mgr = BackupManager(cfg)

    status = mgr.get_status()
    assert status["directory_exists"] is False
    assert status["today_done"] is False
    assert status["total_backups"] == 0
    assert status["today_backup"] is None
    assert status["backups"] == []


def test_backup_empty_directory(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    cfg = AppConfig(backup=BackupConfig(backup_dir=str(backup_dir)))
    mgr = BackupManager(cfg)

    status = mgr.get_status()
    assert status["directory_exists"] is True
    assert status["today_done"] is False
    assert status["total_backups"] == 0
    assert status["today_backup"] is None
    assert status["backups"] == []


def test_backup_with_older_backups_only(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    old_date = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
    old_file = backup_dir / f"janus_backup_{old_date}_03-00-00.tar.gz"
    old_file.write_bytes(b"x" * 1024 * 1024)  # 1 MB

    cfg = AppConfig(backup=BackupConfig(backup_dir=str(backup_dir)))
    mgr = BackupManager(cfg)

    status = mgr.get_status()
    assert status["directory_exists"] is True
    assert status["today_done"] is False
    assert status["total_backups"] == 1
    assert status["today_backup"] is None
    assert status["latest_backup"] is not None
    assert status["latest_backup"]["filename"] == old_file.name
    assert status["latest_backup"]["is_today"] is False
    assert status["latest_backup"]["relative_time"] == "2 days ago"


def test_backup_with_today_backup(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    today_str = date.today().strftime("%Y-%m-%d")
    today_file = backup_dir / f"janus_backup_{today_str}_03-00-01.tar.gz"
    today_file.write_bytes(b"x" * (1024 * 1024 * 10))  # 10 MB

    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_file = backup_dir / f"janus_backup_{yesterday_str}_03-00-00.tar.gz"
    yesterday_file.write_bytes(b"x" * (1024 * 1024 * 8))  # 8 MB

    cfg = AppConfig(backup=BackupConfig(backup_dir=str(backup_dir)))
    mgr = BackupManager(cfg)

    status = mgr.get_status()
    assert status["directory_exists"] is True
    assert status["today_done"] is True
    assert status["today_backup"] is not None
    assert status["today_backup"]["filename"] == today_file.name
    assert status["today_backup"]["is_today"] is True
    assert status["today_backup"]["size_formatted"] == "10.0 MB"
    assert status["total_backups"] == 2
    assert status["total_size_bytes"] == (10 + 8) * 1024 * 1024


@pytest.mark.asyncio
async def test_backup_status_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/backup/status")
        assert response.status_code == 200
        data = response.json()
        assert "today_done" in data
        assert "total_backups" in data
        assert "backups" in data
        assert "rclone_remote" in data


@pytest.mark.asyncio
async def test_backup_trigger_auth_protection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Without PIN
        response = await client.post("/api/backup/trigger", json={})
        assert response.status_code == 401

        # With wrong PIN
        response = await client.post("/api/backup/trigger", json={"pin": "wrong"})
        assert response.status_code == 401
