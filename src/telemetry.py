"""Hardware and system telemetry collector for JanusDeck.

Asynchronously inspects CPU, RAM, Disk storage pools, and NVIDIA GPU metrics
without blocking the async event loop, with graceful fallbacks.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import platform
import time
from typing import Any, Dict, List, Optional
import psutil

from src.config import AppConfig, get_config

logger = logging.getLogger("janus.telemetry")

# Global NVML state
_nvml_initialized = False
_nvml_attempted = False
_nvml_error: Optional[str] = None

import warnings

try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        import pynvml  # type: ignore
    PYNVML_AVAILABLE = True
except ImportError:
    pynvml = None
    PYNVML_AVAILABLE = False


def _init_nvml_if_needed() -> bool:
    """Attempts to initialize NVML safely once."""
    global _nvml_initialized, _nvml_attempted, _nvml_error
    if _nvml_initialized:
        return True
    if _nvml_attempted:
        return False

    _nvml_attempted = True
    if not PYNVML_AVAILABLE:
        _nvml_error = "pynvml library is not installed."
        logger.info("NVIDIA telemetry disabled: %s", _nvml_error)
        return False

    try:
        pynvml.nvmlInit()
        _nvml_initialized = True
        logger.info("NVML initialized successfully.")
        return True
    except Exception as exc:  # Handles pynvml.NVMLError and generic driver errors
        _nvml_error = f"NVML init failed: {exc}"
        logger.warning("NVIDIA NVML could not be initialized: %s", exc)
        return False


def _bytes_to_gb(b: int, decimals: int = 2) -> float:
    return round(b / (1024 ** 3), decimals)


def _get_cpu_temperature() -> Optional[float]:
    """Retrieve CPU temperature from psutil if supported by the host OS (Linux)."""
    if not hasattr(psutil, "sensors_temperatures"):
        return None

    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return None

        # Common sensor group names on Linux
        priority_groups = ["coretemp", "k10temp", "cpu_thermal", "zenpower", "acpitz"]
        for group in priority_groups:
            if group in temps and temps[group]:
                for entry in temps[group]:
                    if entry.current is not None and entry.current > 0:
                        return round(entry.current, 1)

        # Fallback to the first non-empty group
        for entries in temps.values():
            for entry in entries:
                if entry.current is not None and entry.current > 0:
                    return round(entry.current, 1)
    except Exception as exc:
        logger.debug("Failed to read CPU temperatures: %s", exc)

    return None


def _collect_cpu_sync(config: AppConfig) -> Dict[str, Any]:
    """Synchronous CPU stats collection."""
    cpu_conf = config.telemetry.cpu
    if not cpu_conf.enabled:
        return {"enabled": False}

    # interval=None uses non-blocking time delta since last call
    usage_percent = psutil.cpu_percent(interval=None)
    per_core = psutil.cpu_percent(interval=None, percpu=True)

    freq_info = None
    try:
        freq = psutil.cpu_freq()
        if freq:
            freq_info = {
                "current_mhz": round(freq.current, 1),
                "min_mhz": round(freq.min, 1) if freq.min else None,
                "max_mhz": round(freq.max, 1) if freq.max else None,
            }
    except Exception:
        pass

    temp_c = _get_cpu_temperature() if cpu_conf.track_temperatures else None

    return {
        "enabled": True,
        "label": cpu_conf.label,
        "usage_percent": round(usage_percent, 1),
        "per_core_percent": [round(p, 1) for p in per_core],
        "core_count_logical": psutil.cpu_count(logical=True),
        "core_count_physical": psutil.cpu_count(logical=False),
        "frequency": freq_info,
        "temperature_c": temp_c,
    }


def _collect_memory_sync(config: AppConfig) -> Dict[str, Any]:
    """Synchronous RAM & Swap stats collection."""
    mem_conf = config.telemetry.memory
    if not mem_conf.enabled:
        return {"enabled": False}

    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "enabled": True,
        "label": mem_conf.label,
        "total_bytes": vm.total,
        "used_bytes": vm.used,
        "available_bytes": vm.available,
        "total_gb": _bytes_to_gb(vm.total),
        "used_gb": _bytes_to_gb(vm.used),
        "available_gb": _bytes_to_gb(vm.available),
        "usage_percent": round(vm.percent, 1),
        "swap": {
            "total_gb": _bytes_to_gb(swap.total),
            "used_gb": _bytes_to_gb(swap.used),
            "free_gb": _bytes_to_gb(swap.free),
            "usage_percent": round(swap.percent, 1),
        },
    }


def _collect_storage_sync(config: AppConfig) -> Dict[str, Any]:
    """Synchronous storage pools stats collection."""
    pools_data: List[Dict[str, Any]] = []

    for pool in config.telemetry.storage.pools:
        try:
            usage = psutil.disk_usage(pool.path)
            pools_data.append({
                "name": pool.name,
                "path": pool.path,
                "available": True,
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "total_gb": _bytes_to_gb(usage.total),
                "used_gb": _bytes_to_gb(usage.used),
                "free_gb": _bytes_to_gb(usage.free),
                "usage_percent": round(usage.percent, 1),
            })
        except (FileNotFoundError, PermissionError, OSError) as exc:
            pools_data.append({
                "name": pool.name,
                "path": pool.path,
                "available": False,
                "error": str(exc),
                "total_gb": 0.0,
                "used_gb": 0.0,
                "free_gb": 0.0,
                "usage_percent": 0.0,
            })

    return {
        "pools": pools_data,
    }


def _collect_gpu_sync(config: AppConfig) -> Dict[str, Any]:
    """Synchronous NVIDIA GPU stats collection via NVML."""
    gpu_conf = config.telemetry.gpu
    if not gpu_conf.enabled or gpu_conf.type.lower() != "nvidia":
        return {
            "enabled": False,
            "available": False,
            "status": "Disabled in configuration",
        }

    if not _init_nvml_if_needed():
        return {
            "enabled": True,
            "available": False,
            "label": gpu_conf.label,
            "status": _nvml_error or "NVIDIA NVML not available",
        }

    try:
        device_idx = gpu_conf.device_index
        handle = pynvml.nvmlDeviceGetHandleByIndex(device_idx)
        raw_name = pynvml.nvmlDeviceGetName(handle)
        device_name = raw_name.decode("utf-8") if isinstance(raw_name, bytes) else str(raw_name)

        # Utilization
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_percent = utilization.gpu
        memory_percent = utilization.memory

        # Memory info
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        total_vram_gb = _bytes_to_gb(mem_info.total)
        used_vram_gb = _bytes_to_gb(mem_info.used)
        free_vram_gb = _bytes_to_gb(mem_info.free)
        vram_usage_percent = round((mem_info.used / mem_info.total) * 100, 1) if mem_info.total > 0 else 0.0

        # Temperature
        temp_c = None
        if gpu_conf.track_temp:
            try:
                temp_c = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            except Exception:
                pass

        # Power Usage (milliwatts -> watts)
        power_w = None
        try:
            power_mw = pynvml.nvmlDeviceGetPowerUsage(handle)
            power_w = round(power_mw / 1000.0, 1)
        except Exception:
            pass

        return {
            "enabled": True,
            "available": True,
            "label": gpu_conf.label or device_name,
            "device_name": device_name,
            "device_index": device_idx,
            "usage_percent": gpu_percent,
            "memory_usage_percent": vram_usage_percent,
            "vram": {
                "total_bytes": mem_info.total,
                "used_bytes": mem_info.used,
                "free_bytes": mem_info.free,
                "total_gb": total_vram_gb,
                "used_gb": used_vram_gb,
                "free_gb": free_vram_gb,
                "usage_percent": vram_usage_percent,
            },
            "temperature_c": temp_c,
            "power_watts": power_w,
        }
    except Exception as exc:
        logger.error("Error reading NVIDIA GPU telemetry: %s", exc)
        return {
            "enabled": True,
            "available": False,
            "label": gpu_conf.label,
            "error": str(exc),
        }


def _collect_host_sync() -> Dict[str, Any]:
    """Synchronous host and OS metadata collection."""
    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)

    return {
        "hostname": platform.node(),
        "os": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "uptime_seconds": uptime_seconds,
        "boot_timestamp": datetime.fromtimestamp(boot_time, tz=timezone.utc).isoformat(),
    }


def _collect_all_sync(config: AppConfig) -> Dict[str, Any]:
    """Executes all telemetry probes synchronously in a worker thread."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": _collect_host_sync(),
        "cpu": _collect_cpu_sync(config),
        "memory": _collect_memory_sync(config),
        "gpu": _collect_gpu_sync(config),
        "storage": _collect_storage_sync(config),
    }


class TelemetryCollector:
    """Telemetry collector engine that dispatches work to thread pools."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        # Prime psutil CPU counters on initialization
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)

    async def get_metrics(self) -> Dict[str, Any]:
        """Asynchronously gathers all system telemetry without blocking the async event loop."""
        return await asyncio.to_thread(_collect_all_sync, self.config)


# Global collector instance
_collector: Optional[TelemetryCollector] = None


def get_telemetry_collector(config: Optional[AppConfig] = None) -> TelemetryCollector:
    global _collector
    if _collector is None:
        _collector = TelemetryCollector(config or get_config())
    return _collector
