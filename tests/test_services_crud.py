"""Tests for dynamic service management and CRUD API."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.main import app
from src.db.session import get_db
from src.db.models import Service


@pytest.fixture
def mock_service():
    return Service(
        id="srv-123",
        name="Coolify PaaS",
        category="Infrastructure & Platform",
        url="http://192.168.1.68:8000",
        external_url="http://10.8.0.1:8000",
        health_check_url="http://192.168.1.68:8000",
        icon="server",
        description="Self-hosted Git-push deployment engine",
        display_order=0,
        is_enabled=True,
    )


@pytest.mark.asyncio
async def test_get_categories():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/services/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert isinstance(data["categories"], list)


@pytest.mark.asyncio
async def test_create_service_unauthorized():
    payload = {
        "name": "New Service",
        "category": "Tools",
        "url": "http://192.168.1.50:3000",
        "icon": "tool",
        "pin": "9999",  # Wrong PIN
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/services", json=payload)
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_service_without_db():
    payload = {
        "name": "New Service",
        "category": "Tools",
        "url": "http://192.168.1.50:3000",
        "icon": "globe",
        "pin": "2070",
    }
    # When get_db yields None (no DB connected)
    async def override_none_db():
        yield None

    app.dependency_overrides[get_db] = override_none_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/services", json=payload)
            assert response.status_code == 503
            assert "PostgreSQL database is not connected" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_create_service_success(mock_service):
    payload = {
        "name": "Coolify PaaS",
        "category": "Infrastructure & Platform",
        "url": "http://192.168.1.68:8000",
        "external_url": "http://10.8.0.1:8000",
        "icon": "server",
        "description": "Self-hosted Git-push deployment engine",
        "pin": "2070",
    }

    mock_session = AsyncMock()

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_db
    try:
        with patch("src.main.create_service", return_value=mock_service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/services", json=payload)
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "created"
                assert data["service"]["name"] == "Coolify PaaS"
                assert data["service"]["id"] == "srv-123"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_update_service_success(mock_service):
    payload = {
        "name": "Coolify PaaS v4",
        "description": "Updated PaaS",
        "pin": "2070",
    }

    mock_session = AsyncMock()

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_db
    try:
        with patch("src.main.update_service", return_value=mock_service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.put("/api/services/srv-123", json=payload)
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "updated"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_update_service_not_found():
    payload = {
        "name": "Coolify PaaS v4",
        "pin": "2070",
    }

    mock_session = AsyncMock()

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_db
    try:
        with patch("src.main.update_service", return_value=None):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.put("/api/services/non-existent", json=payload)
                assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_delete_service_success():
    mock_session = AsyncMock()

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_db
    try:
        with patch("src.main.delete_service", return_value=True):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.delete("/api/services/srv-123?pin=2070")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "deleted"
                assert data["id"] == "srv-123"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_reorder_services():
    mock_session = AsyncMock()

    async def override_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_db
    try:
        with patch("src.main.reorder_services", return_value=True):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.patch(
                    "/api/services/reorder",
                    json={"orders": [{"id": "srv-1", "display_order": 1}], "pin": "2070"},
                )
                assert response.status_code == 200
                assert response.json()["status"] == "reordered"
    finally:
        app.dependency_overrides.pop(get_db, None)
