import os
from pathlib import Path
import pytest
from src.config import load_config, find_config_path, AppConfig


def test_find_config_path_default():
    path = find_config_path()
    assert path.is_file()
    assert path.name in ("config.yaml", "config.example.yaml")


def test_load_config_values():
    config = load_config(reload=True)
    assert isinstance(config, AppConfig)
    assert config.server.port == 8080
    assert config.server.title == "Janus Lab"
    assert config.security.master_pin == "2070"
    assert config.telemetry.cpu.enabled is True
    assert config.telemetry.memory.enabled is True


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("JANUS_PIN", "9999")
    monkeypatch.setenv("JANUS_PORT", "9090")
    monkeypatch.setenv("JANUS_HOST", "127.0.0.1")

    config = load_config(reload=True)
    assert config.security.master_pin == "9999"
    assert config.server.port == 9090
    assert config.server.host == "127.0.0.1"


def test_public_dict_strips_pin():
    config = load_config(reload=True)
    public_dict = config.to_public_dict()
    assert "master_pin" not in public_dict["security"]
    assert public_dict["security"]["pin_required"] is True
