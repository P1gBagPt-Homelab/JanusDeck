"""JanusDeck FastAPI Main Application.

Exposes REST APIs and SSE streaming for hardware telemetry,
service health checks, and frontend static assets.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from src.config import get_config
from src.services import check_all_services
from src.telemetry import get_telemetry_collector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("janus.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    logger.info("JanusDeck backend starting on port %s", config.server.port)
    # Prime telemetry collector
    get_telemetry_collector(config)
    yield
    logger.info("JanusDeck backend shutting down.")


app = FastAPI(
    title="JanusDeck API",
    description="Backend engine and hardware telemetry pipeline for Project Janus homelab.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local development and cross-origin embedding if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure web directories exist
STATIC_DIR = Path("web/static")
TEMPLATES_DIR = Path("web/templates")
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Mount static directory
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/health")
async def health_check():
    """Application health probe."""
    return {
        "status": "ok",
        "app": "JanusDeck",
        "version": "1.0.0",
    }


@app.get("/api/config")
async def get_public_configuration():
    """Returns safe, public configuration details for client UI consumption."""
    config = get_config()
    return config.to_public_dict()


@app.get("/api/stats/snapshot")
async def get_stats_snapshot():
    """Returns a single real-time snapshot of all hardware telemetry metrics."""
    collector = get_telemetry_collector()
    return await collector.get_metrics()


@app.get("/api/stats")
async def stream_telemetry_events(request: Request, count: int | None = None):
    """Server-Sent Events (SSE) endpoint broadcasting live hardware metrics.

    Broadcasts updates at the configured interval (default 2 seconds).
    Optionally accepts a `count` parameter to stream a fixed number of frames.
    """
    config = get_config()
    interval_seconds = max(0.5, config.server.refresh_interval_ms / 1000.0)
    collector = get_telemetry_collector(config)

    async def event_generator() -> AsyncGenerator[str, None]:
        sent = 0
        try:
            while True:
                if count is not None and sent >= count:
                    break
                if await request.is_disconnected():
                    logger.debug("SSE client disconnected.")
                    break

                metrics = await collector.get_metrics()
                yield f"data: {json.dumps(metrics)}\n\n"
                sent += 1
                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.debug("SSE stream cancelled.")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx / reverse proxy buffer bypass
        },
    )


@app.get("/api/services")
async def get_services_status():
    """Evaluates HTTP health checks across all configured homelab services."""
    config = get_config()
    services_status = await check_all_services(config)
    return {
        "services": services_status,
    }


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the dashboard index HTML."""
    index_file = TEMPLATES_DIR / "index.html"
    if index_file.is_file():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))

    # Fallback placeholder HTML until Phase 3 UI is built
    config = get_config()
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{config.server.title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{ background: #0b0f19; color: #f8fafc; font-family: -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
    .card {{ background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 2rem; max-width: 500px; text-align: center; }}
    h1 {{ color: #38bdf8; margin-top: 0; }}
    a {{ color: #a855f7; text-decoration: none; }}
    code {{ background: #1e293b; padding: 0.2rem 0.4rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{config.server.title}</h1>
    <p>{config.server.subtitle}</p>
    <p>Backend API Engine is active (Phase 1 Ready).</p>
    <p>Inspect live endpoints: <a href="/docs">Swagger API Docs</a> | <a href="/api/stats/snapshot">Stats Snapshot</a> | <a href="/api/config">Config</a></p>
  </div>
</body>
</html>
""")


if __name__ == "__main__":
    import uvicorn
    cfg = get_config()
    uvicorn.run("src.main:app", host=cfg.server.host, port=cfg.server.port, reload=True)
