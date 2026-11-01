import httpx
import pytest
from src.config import ServiceItem, load_config
from src.services import ping_service, check_all_services


@pytest.mark.asyncio
async def test_ping_service_success():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "healthy"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        item = ServiceItem(name="Test Service", url="http://test.local/health")
        result = await ping_service(item, client)
        assert result["status"] == "online"
        assert result["status_code"] == 200
        assert result["latency_ms"] is not None


@pytest.mark.asyncio
async def test_ping_service_degraded():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Bad Gateway")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        item = ServiceItem(name="Degraded Service", url="http://test.local/502")
        result = await ping_service(item, client)
        assert result["status"] == "degraded"
        assert result["status_code"] == 502


@pytest.mark.asyncio
async def test_ping_service_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        item = ServiceItem(name="Timeout Service", url="http://test.local/timeout")
        result = await ping_service(item, client)
        assert result["status"] == "offline"
        assert "timed out" in result["error"].lower()
