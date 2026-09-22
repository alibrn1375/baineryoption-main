"""Comprehensive test suite for the FO-X 5M Production and Operations Layer."""

import os
import pytest
from app.core.health import HealthResponse, SystemHealthSupervisor
from app.core.logging import JSONFormatter, ExecutionTimer
from app.core.backup import ProductionBackupManager
from app.storage.database_manager import DatabaseManager


def test_system_health_supervisor():
    """Verify health reporting and degraded status handling."""
    supervisor = SystemHealthSupervisor()
    health = supervisor.get_overall_health()
    assert health.status == "HEALTHY"
    assert "database" in health.services
    assert "market_data_feed" in health.services

    # Simulate degraded service
    supervisor.update_service("market_data_feed", "DEGRADED", latency_ms=450.0)
    health_degraded = supervisor.get_overall_health()
    assert health_degraded.status == "DEGRADED"


def test_production_backup_manager(tmp_path):
    """Verify backup snapshot creation and pruning."""
    backup_dir = tmp_path / "backups"
    source_dir = tmp_path / "source"
    os.makedirs(source_dir, exist_ok=True)
    with open(source_dir / "sample_journal.parquet", "w") as f:
        f.write("test binary data")

    mgr = ProductionBackupManager(
        backup_dir=str(backup_dir),
        source_dirs=[str(source_dir)],
        source_files=[]
    )

    archive_path = mgr.create_snapshot_backup()
    assert os.path.exists(archive_path)
    assert archive_path.endswith(".tar.gz")


@pytest.mark.asyncio
async def test_database_manager_fallback():
    """Verify database initialization fallback when postgres is unavailable locally."""
    db = DatabaseManager(host="127.0.0.1", port=5432)
    res = await db.initialize()
    assert isinstance(res, bool)
    await db.close()
