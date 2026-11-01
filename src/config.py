"""Configuration management for JanusDeck.

Loads and validates YAML configuration with fallback environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    title: str = "Janus Lab"
    subtitle: str = "Hybrid Gaming & On-Demand Server"
    port: int = 8080
    host: str = "0.0.0.0"
    refresh_interval_ms: int = 2000


class SecurityConfig(BaseModel):
    pin_required: bool = True
    master_pin: str = "2070"
    session_timeout_seconds: int = 300
    max_failed_attempts: int = 5
    lockout_duration_seconds: int = 60


class OSTarget(BaseModel):
    id: str
    name: str
    icon: str = "hard-drive"
    grub_entry: str
    description: Optional[str] = None


class PowerConfig(BaseModel):
    allow_shutdown: bool = True
    allow_reboot: bool = True
    allow_os_switch: bool = True
    grub_cfg_path: str = "/boot/grub/grub.cfg"
    grubenv_path: str = "/boot/grub/grubenv"
    dbus_socket_path: str = "/var/run/dbus/system_bus_socket"
    simulate: bool = False
    os_targets: List[OSTarget] = Field(default_factory=list)


class CpuTelemetryConfig(BaseModel):
    enabled: bool = True
    label: str = "CPU"
    track_temperatures: bool = True


class MemoryTelemetryConfig(BaseModel):
    enabled: bool = True
    label: str = "System Memory"
    total_gb: Optional[float] = None


class GpuTelemetryConfig(BaseModel):
    enabled: bool = True
    type: str = "nvidia"  # "nvidia" or "none"
    label: str = "NVIDIA GPU"
    track_vram: bool = True
    track_temp: bool = True
    device_index: int = 0


class StoragePoolConfig(BaseModel):
    name: str
    path: str


class StorageTelemetryConfig(BaseModel):
    pools: List[StoragePoolConfig] = Field(default_factory=list)


class TelemetryConfig(BaseModel):
    cpu: CpuTelemetryConfig = Field(default_factory=CpuTelemetryConfig)
    memory: MemoryTelemetryConfig = Field(default_factory=MemoryTelemetryConfig)
    gpu: GpuTelemetryConfig = Field(default_factory=GpuTelemetryConfig)
    storage: StorageTelemetryConfig = Field(default_factory=StorageTelemetryConfig)


class ServiceItem(BaseModel):
    name: str
    url: str
    external_url: Optional[str] = None
    icon: str = "globe"
    description: Optional[str] = None
    health_check_url: Optional[str] = None


class ServiceCategory(BaseModel):
    category: str
    items: List[ServiceItem] = Field(default_factory=list)


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    power: PowerConfig = Field(default_factory=PowerConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    services: List[ServiceCategory] = Field(default_factory=list)

    def to_public_dict(self) -> dict:
        """Returns a sanitized dict safe to expose to client/frontend (excluding secrets)."""
        data = self.model_dump()
        # Strip master PIN from public consumption
        if "security" in data:
            data["security"] = {
                "pin_required": data["security"].get("pin_required", True),
                "session_timeout_seconds": data["security"].get("session_timeout_seconds", 300),
            }
        return data


_cached_config: Optional[AppConfig] = None


def find_config_path(explicit_path: Optional[str] = None) -> Path:
    """Find the best configuration file path."""
    if explicit_path:
        return Path(explicit_path)

    env_path = os.getenv("JANUS_CONFIG_PATH") or os.getenv("JANUS_CONFIG")
    if env_path and Path(env_path).is_file():
        return Path(env_path)

    candidates = [
        Path("config.yaml"),
        Path("/app/config.yaml"),
        Path("config.example.yaml"),
        Path("/app/config.example.yaml"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return Path("config.yaml")


def load_config(path: Optional[str] = None, reload: bool = False) -> AppConfig:
    """Load configuration from YAML file and apply environment variable overrides."""
    global _cached_config
    if _cached_config is not None and not reload:
        return _cached_config

    config_path = find_config_path(path)
    raw_data: dict = {}

    if config_path.is_file():
        with open(config_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

    config = AppConfig(**raw_data)

    # Environment variable overrides
    if env_pin := (os.getenv("JANUS_PIN") or os.getenv("MASTER_PIN")):
        config.security.master_pin = env_pin

    if env_port := (os.getenv("JANUS_PORT") or os.getenv("PORT")):
        try:
            config.server.port = int(env_port)
        except ValueError:
            pass

    if env_host := (os.getenv("JANUS_HOST") or os.getenv("HOST")):
        config.server.host = env_host

    if env_interval := os.getenv("JANUS_REFRESH_INTERVAL_MS"):
        try:
            config.server.refresh_interval_ms = int(env_interval)
        except ValueError:
            pass

    if env_sim := os.getenv("JANUS_SIMULATE_POWER"):
        config.power.simulate = env_sim.strip().lower() in ("1", "true", "yes", "on")

    if env_grub_cfg := os.getenv("JANUS_GRUB_CFG_PATH"):
        config.power.grub_cfg_path = env_grub_cfg

    if env_grubenv := os.getenv("JANUS_GRUBENV_PATH"):
        config.power.grubenv_path = env_grubenv

    if env_dbus_socket := os.getenv("JANUS_DBUS_SOCKET_PATH"):
        config.power.dbus_socket_path = env_dbus_socket

    _cached_config = config
    return config


def get_config() -> AppConfig:
    """Retrieve the active configuration instance."""
    return load_config()
