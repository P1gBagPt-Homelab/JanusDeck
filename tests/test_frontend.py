"""Tests for Svelte 5 Frontend Application & Static Assets.

Verifies that the compiled Svelte 5 SPA, JavaScript bundles, CSS stylesheets,
and asset routes are properly mounted and served by FastAPI.
"""

from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_root_serves_svelte_dashboard():
    """Verify that GET / serves the compiled Svelte 5 dashboard SPA."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        html = response.text

        # Verify HTML5 structure & title
        assert "<!DOCTYPE html>" in html
        assert "Janus Lab" in html
        assert "JanusDeck" in html

        # Verify Svelte 5 SPA root container and assets
        assert 'id="app"' in html
        assert '/assets/' in html


@pytest.mark.asyncio
async def test_svelte_js_asset_served():
    """Verify that compiled Svelte 5 JS bundles are mounted and accessible under /assets."""
    assets_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "assets"
    assert assets_dir.is_dir(), "frontend/dist/assets must exist"
    js_files = list(assets_dir.glob("*.js"))
    assert len(js_files) > 0, "At least one JS bundle must exist"
    
    asset_name = js_files[0].name
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/assets/{asset_name}")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")
        assert len(response.text) > 1000


@pytest.mark.asyncio
async def test_svelte_css_asset_served():
    """Verify that compiled Svelte 5 CSS bundles are mounted and accessible under /assets."""
    assets_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "assets"
    css_files = list(assets_dir.glob("*.css"))
    assert len(css_files) > 0, "At least one CSS bundle must exist"

    asset_name = css_files[0].name
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/assets/{asset_name}")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")
        assert len(response.text) > 500
