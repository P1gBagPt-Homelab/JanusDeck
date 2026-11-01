import json
import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app"] == "JanusDeck"


@pytest.mark.asyncio
async def test_config_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "server" in data
        assert "security" in data
        assert "master_pin" not in data["security"]


@pytest.mark.asyncio
async def test_stats_snapshot_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/stats/snapshot")
        assert response.status_code == 200
        data = response.json()
        assert "cpu" in data
        assert "memory" in data
        assert "storage" in data
        assert "host" in data


@pytest.mark.asyncio
async def test_root_index_html():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "Janus" in response.text


@pytest.mark.asyncio
async def test_stats_sse_stream():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("GET", "/api/stats?count=1") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            
            chunk_received = False
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    payload = json.loads(line[5:].strip())
                    assert "cpu" in payload
                    assert "memory" in payload
                    chunk_received = True
                    break
            assert chunk_received is True
