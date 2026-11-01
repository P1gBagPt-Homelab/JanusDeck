import pytest
from src.config import load_config
from src.telemetry import TelemetryCollector, get_telemetry_collector


@pytest.mark.asyncio
async def test_telemetry_collector_returns_all_metrics():
    config = load_config(reload=True)
    collector = TelemetryCollector(config)
    metrics = await collector.get_metrics()

    assert "timestamp" in metrics
    assert "host" in metrics
    assert "cpu" in metrics
    assert "memory" in metrics
    assert "gpu" in metrics
    assert "storage" in metrics

    # Host assertions
    host = metrics["host"]
    assert "hostname" in host
    assert "os" in host
    assert "uptime_seconds" in host
    assert host["uptime_seconds"] >= 0

    # CPU assertions
    cpu = metrics["cpu"]
    assert cpu["enabled"] is True
    assert "usage_percent" in cpu
    assert 0.0 <= cpu["usage_percent"] <= 100.0
    assert "core_count_logical" in cpu
    assert cpu["core_count_logical"] > 0

    # Memory assertions
    mem = metrics["memory"]
    assert mem["enabled"] is True
    assert "total_gb" in mem
    assert mem["total_gb"] > 0
    assert "usage_percent" in mem
    assert 0.0 <= mem["usage_percent"] <= 100.0

    # Storage assertions
    storage = metrics["storage"]
    assert "pools" in storage
    assert len(storage["pools"]) > 0

    # GPU assertions (NVML handles unavailability gracefully)
    gpu = metrics["gpu"]
    assert "enabled" in gpu
    if not gpu.get("available"):
        assert "status" in gpu or "error" in gpu
