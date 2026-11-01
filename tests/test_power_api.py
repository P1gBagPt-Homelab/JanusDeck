from httpx import ASGITransport, AsyncClient
import pytest
from src.config import get_config
from src.main import app
from src.security import get_security_gate


@pytest.fixture(autouse=True)
def reset_security_gate():
    """Reset security gate state before each test."""
    gate = get_security_gate()
    gate.reset_client("127.0.0.1")
    gate.reset_client("test_client")


@pytest.mark.asyncio
async def test_api_auth_verify_success():
    config = get_config()
    master_pin = config.security.master_pin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/verify", json={"pin": master_pin})
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert "successfully" in data["message"]


@pytest.mark.asyncio
async def test_api_auth_verify_invalid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/verify", json={"pin": "wrong_pin"})
        assert resp.status_code == 401
        data = resp.json()
        assert data["valid"] is False
        assert "remaining_attempts" in data


@pytest.mark.asyncio
async def test_api_auth_lockout_rate_limit():
    gate = get_security_gate()
    gate.reset_client("127.0.0.1")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Exhaust 5 attempts
        for _ in range(5):
            await client.post("/api/auth/verify", json={"pin": "0000"})

        # 6th attempt should be HTTP 429
        resp = await client.post("/api/auth/verify", json={"pin": "0000"})
        assert resp.status_code == 429
        data = resp.json()
        assert "remaining_lockout_seconds" in data


@pytest.mark.asyncio
async def test_api_power_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/power/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "allow_reboot" in data
        assert "allow_shutdown" in data
        assert "allow_os_switch" in data
        assert "simulate_mode" in data
        assert "os_targets" in data


@pytest.mark.asyncio
async def test_api_power_targets():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/power/targets")
        assert resp.status_code == 200
        data = resp.json()
        assert "configured_targets" in data
        assert "discovered_entries" in data


@pytest.mark.asyncio
async def test_api_power_reboot_requires_valid_pin():
    config = get_config()
    master_pin = config.security.master_pin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Invalid PIN
        resp_bad = await client.post("/api/power/reboot", json={"pin": "wrong"})
        assert resp_bad.status_code == 401

        # Valid PIN
        resp_good = await client.post("/api/power/reboot", json={"pin": master_pin})
        assert resp_good.status_code == 200
        data = resp_good.json()
        assert data["status"] == "rebooting"
        assert data["action"] == "Reboot"


@pytest.mark.asyncio
async def test_api_power_shutdown_requires_valid_pin():
    config = get_config()
    master_pin = config.security.master_pin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/power/shutdown", json={"pin": master_pin})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "shutting_down"
        assert data["action"] == "PowerOff"


@pytest.mark.asyncio
async def test_api_power_switch_os():
    config = get_config()
    master_pin = config.security.master_pin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/power/switch-os",
            json={"pin": master_pin, "target_id": "windows"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "switching_os"
        assert "reboot_result" in data


@pytest.mark.asyncio
async def test_api_clear_next_entry():
    config = get_config()
    master_pin = config.security.master_pin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/power/clear-next-entry", json={"pin": master_pin})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cleared"
