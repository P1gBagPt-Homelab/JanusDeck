"""Tests for Phase 3 Frontend Interface & Static Assets.

Verifies that the dashboard HTML, CSS stylesheets, Lucide SVG icon engine,
and application JavaScript are properly served and meet functional requirements.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_root_serves_dashboard():
    """Verify that GET / serves the frontend dashboard (compiled Svelte 5 SPA or template)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        html = response.text

        # Verify HTML5 structure & title
        assert "<!DOCTYPE html>" in html
        assert "Janus Lab" in html
        assert "JanusDeck" in html

        # Verify either Svelte 5 SPA root or vanilla static template
        assert ('id="app"' in html and '/assets/' in html) or ('/static/css/styles.css' in html)


@pytest.mark.asyncio
async def test_svelte_assets_served():
    """Verify that compiled Svelte 5 assets are mounted and accessible under /assets."""
    from pathlib import Path
    assets_dir = Path(__file__).resolve().parent.parent / "web" / "dist" / "assets"
    if assets_dir.is_dir():
        asset_files = list(assets_dir.glob("*.js"))
        if asset_files:
            asset_name = asset_files[0].name
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(f"/assets/{asset_name}")
                assert response.status_code == 200
                assert "javascript" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_static_stylesheet_served():
    """Verify that /static/css/styles.css is accessible and contains design tokens."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/static/css/styles.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")
        css = response.text

        # Verify theme variables
        assert "--bg-ground: #0b0f19" in css
        assert "--text-primary: #f8fafc" in css
        assert "--accent-cyan: #38bdf8" in css
        assert "tabular-nums" in css
        assert "keypad-grid" in css
        assert "countdown-circle-wrap" in css


@pytest.mark.asyncio
async def test_static_icons_served():
    """Verify that /static/js/icons.js is accessible and contains icon definitions."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/static/js/icons.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")
        js = response.text
        assert "JanusIcons" in js
        assert "gamepad" in js
        assert "server" in js
        assert "power" in js


@pytest.mark.asyncio
async def test_static_app_js_served():
    """Verify that /static/js/app.js is accessible and implements state logic."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/static/js/app.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")
        js = response.text
        assert "/api/stats" in js
        assert "/api/power/status" in js
        assert "/api/services" in js
        assert "proceedToCountdown" in js
        assert "executePendingPowerAction" in js
        assert "clearNextEntryAction" in js
