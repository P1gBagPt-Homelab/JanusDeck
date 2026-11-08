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
from typing import AsyncGenerator, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backup import get_backup_manager
from src.config import get_config
from src.db.crud import (
    create_service,
    delete_service,
    get_distinct_categories,
    reorder_services,
    update_service,
)
from src.db.seeder import seed_services_from_config_if_empty
from src.db.session import close_db, get_db, get_session_factory, init_db
from src.grub import get_grub_manager
from src.power import get_power_service
from src.security import get_security_gate
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

    # Initialize PostgreSQL if configured
    if config.database.url:
        try:
            initialized = await init_db()
            if initialized:
                factory = get_session_factory()
                if factory:
                    async with factory() as session:
                        await seed_services_from_config_if_empty(session, config)
        except Exception as exc:
            logger.error("Database initialization failed on startup: %s", exc)

    yield

    logger.info("JanusDeck backend shutting down.")
    await close_db()


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

# Frontend SPA directories
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
ASSETS_DIR = FRONTEND_DIST / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Mount Vite assets directory
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


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


# ==============================================================================
# Service Models & CRUD Endpoints
# ==============================================================================

class ServiceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=500)
    external_url: Optional[str] = None
    health_check_url: Optional[str] = None
    icon: str = "globe"
    description: Optional[str] = None
    display_order: int = 0
    is_enabled: bool = True
    pin: Optional[str] = None


class ServiceUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    external_url: Optional[str] = None
    health_check_url: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_enabled: Optional[bool] = None
    pin: Optional[str] = None


class ReorderItem(BaseModel):
    id: str
    display_order: int


class ServiceReorderRequest(BaseModel):
    orders: List[ReorderItem]
    pin: Optional[str] = None


ServiceReorderRequest.model_rebuild()


@app.get("/api/services")
async def get_services_status(db: Optional[AsyncSession] = Depends(get_db)):
    """Evaluates HTTP health checks across all configured homelab services."""
    config = get_config()
    services_status = await check_all_services(config=config, session=db)
    return {
        "services": services_status,
    }


@app.get("/api/services/categories")
async def get_service_categories(db: Optional[AsyncSession] = Depends(get_db)):
    """Returns list of distinct service categories for auto-suggestions."""
    if db is not None:
        try:
            categories = await get_distinct_categories(db)
            if categories:
                return {"categories": categories}
        except Exception as exc:
            logger.warning("Could not fetch categories from database: %s", exc)

    config = get_config()
    cats = list(dict.fromkeys(c.category for c in config.services if c.category))
    return {"categories": cats}


@app.post("/api/services")
async def create_new_service(
    req: ServiceCreateRequest,
    request: Request,
    db: Optional[AsyncSession] = Depends(get_db),
):
    """Creates a new homelab service (requires Master PIN)."""
    check_auth_request(request, req.pin)
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL database is not connected. Configure DATABASE_URL in environment.",
        )
    data = req.model_dump(exclude={"pin"})
    created = await create_service(db, data)
    return {"status": "created", "service": created.to_dict()}


@app.put("/api/services/{service_id}")
async def update_existing_service(
    service_id: str,
    req: ServiceUpdateRequest,
    request: Request,
    db: Optional[AsyncSession] = Depends(get_db),
):
    """Updates an existing homelab service (requires Master PIN)."""
    check_auth_request(request, req.pin)
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL database is not connected. Configure DATABASE_URL in environment.",
        )
    data = req.model_dump(exclude={"pin"}, exclude_unset=True)
    updated = await update_service(db, service_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return {"status": "updated", "service": updated.to_dict()}


@app.delete("/api/services/{service_id}")
async def delete_existing_service(
    service_id: str,
    request: Request,
    pin: Optional[str] = None,
    db: Optional[AsyncSession] = Depends(get_db),
):
    """Deletes a homelab service (requires Master PIN)."""
    check_auth_request(request, pin)
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL database is not connected. Configure DATABASE_URL in environment.",
        )
    deleted = await delete_service(db, service_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return {"status": "deleted", "id": service_id}


@app.patch("/api/services/reorder")
async def reorder_existing_services(
    req: ServiceReorderRequest,
    request: Request,
    db: Optional[AsyncSession] = Depends(get_db),
):
    """Updates display order for services (requires Master PIN)."""
    check_auth_request(request, req.pin)
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL database is not connected. Configure DATABASE_URL in environment.",
        )
    orders = [item.model_dump() for item in req.orders]
    await reorder_services(db, orders)
    return {"status": "reordered"}


# ==============================================================================
# Security & Authentication Models / Routes
# ==============================================================================

class VerifyPinRequest(BaseModel):
    pin: str


class PowerActionRequest(BaseModel):
    pin: Optional[str] = None
    interactive: bool = True


class SwitchOSRequest(BaseModel):
    pin: Optional[str] = None
    target_id: Optional[str] = None
    grub_entry: Optional[str] = None
    interactive: bool = True


def get_client_ip(request: Request) -> str:
    """Extract client IP address from proxy headers or direct socket."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def check_auth_request(request: Request, pin: Optional[str] = None) -> bool:
    """Verifies that the request is authenticated with Master PIN or PIN is not required."""
    config = get_config()
    if not config.security.pin_required:
        return True

    candidate_pin = (
        pin
        or request.headers.get("x-pin")
        or request.headers.get("x-session-pin")
    )
    client_ip = get_client_ip(request)
    gate = get_security_gate()
    is_valid, message, status_detail = gate.verify_pin(candidate_pin, client_id=client_ip)
    if not is_valid:
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if "Locked out" in message
            else status.HTTP_401_UNAUTHORIZED
        )
        raise HTTPException(
            status_code=status_code,
            detail=message,
        )
    return True


@app.post("/api/auth/verify")
async def verify_pin(req: VerifyPinRequest, request: Request):
    """Verifies master PIN against brute-force security gate."""
    client_ip = get_client_ip(request)
    gate = get_security_gate()
    is_valid, message, status_detail = gate.verify_pin(req.pin, client_id=client_ip)

    if is_valid:
        import secrets
        return {
            "valid": True,
            "message": message,
            "session_token": secrets.token_urlsafe(32),
        }

    if "Locked out" in message:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "valid": False,
                "message": message,
                "remaining_lockout_seconds": status_detail,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "valid": False,
            "message": message,
            "remaining_attempts": status_detail,
        },
    )


@app.get("/api/auth/status")
async def auth_status(request: Request):
    """Returns PIN requirement and lockout state for caller."""
    client_ip = get_client_ip(request)
    gate = get_security_gate()
    config = get_config()
    is_locked, remaining = gate.is_locked_out(client_ip)
    return {
        "pin_required": config.security.pin_required,
        "locked_out": is_locked,
        "remaining_lockout_seconds": remaining,
    }


# ==============================================================================
# Host Power & Dual-Boot Bridge Routes
# ==============================================================================

@app.get("/api/power/status")
async def get_power_status():
    """Returns power bridge capabilities, DBus socket status, and active GRUB entry."""
    service = get_power_service()
    return await service.get_power_status()


@app.get("/api/power/targets")
async def get_boot_targets():
    """Returns configured OS targets and discovered GRUB menu entries."""
    config = get_config()
    grub = get_grub_manager(config)
    discovered = grub.parse_menu_entries()
    return {
        "configured_targets": [t.model_dump() for t in config.power.os_targets],
        "discovered_entries": discovered,
    }


@app.post("/api/power/reboot")
async def trigger_reboot(req: PowerActionRequest, request: Request):
    """Triggers graceful host reboot via DBus (requires PIN)."""
    client_ip = get_client_ip(request)
    gate = get_security_gate()

    is_valid, message, status_detail = gate.verify_pin(req.pin, client_id=client_ip)
    if not is_valid:
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if "Locked out" in message
            else status.HTTP_401_UNAUTHORIZED
        )
        return JSONResponse(
            status_code=status_code,
            content={"error": "authentication_failed", "message": message, "detail": status_detail},
        )

    service = get_power_service()
    try:
        result = await service.reboot(interactive=req.interactive)
        return {"status": "rebooting", **result}
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except Exception as exc:
        logger.error("Reboot execution error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@app.post("/api/power/shutdown")
async def trigger_shutdown(req: PowerActionRequest, request: Request):
    """Triggers graceful host poweroff via DBus (requires PIN)."""
    client_ip = get_client_ip(request)
    gate = get_security_gate()

    is_valid, message, status_detail = gate.verify_pin(req.pin, client_id=client_ip)
    if not is_valid:
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if "Locked out" in message
            else status.HTTP_401_UNAUTHORIZED
        )
        return JSONResponse(
            status_code=status_code,
            content={"error": "authentication_failed", "message": message, "detail": status_detail},
        )

    service = get_power_service()
    try:
        result = await service.poweroff(interactive=req.interactive)
        return {"status": "shutting_down", **result}
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except Exception as exc:
        logger.error("Shutdown execution error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@app.post("/api/power/switch-os")
async def trigger_switch_os(req: SwitchOSRequest, request: Request):
    """Sets one-shot GRUB next_entry and reboots machine (requires PIN)."""
    client_ip = get_client_ip(request)
    gate = get_security_gate()

    is_valid, message, status_detail = gate.verify_pin(req.pin, client_id=client_ip)
    if not is_valid:
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if "Locked out" in message
            else status.HTTP_401_UNAUTHORIZED
        )
        return JSONResponse(
            status_code=status_code,
            content={"error": "authentication_failed", "message": message, "detail": status_detail},
        )

    service = get_power_service()
    try:
        result = await service.switch_os(
            target_id=req.target_id,
            grub_entry=req.grub_entry,
            interactive=req.interactive,
        )
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Switch OS execution error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@app.post("/api/power/clear-next-entry")
async def clear_next_entry(req: PowerActionRequest, request: Request):
    """Clears pending GRUB next_entry without rebooting (requires PIN)."""
    client_ip = get_client_ip(request)
    gate = get_security_gate()

    is_valid, message, status_detail = gate.verify_pin(req.pin, client_id=client_ip)
    if not is_valid:
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if "Locked out" in message
            else status.HTTP_401_UNAUTHORIZED
        )
        return JSONResponse(
            status_code=status_code,
            content={"error": "authentication_failed", "message": message, "detail": status_detail},
        )

    grub = get_grub_manager()
    success = await grub.clear_next_entry()
    return {
        "status": "cleared" if success else "failed",
        "message": "Cleared GRUB next_entry." if success else "Failed to clear next_entry.",
    }


# ==============================================================================
# Automated Backups Inspection & Trigger Routes
# ==============================================================================

class BackupTriggerRequest(BaseModel):
    pin: Optional[str] = None
    force: bool = False


@app.get("/api/backup/status")
@app.get("/api/backups")
async def get_backup_status():
    """Inspects local snapshots, checks if today's backup exists, and provides inventory."""
    mgr = get_backup_manager()
    return mgr.get_status()


@app.post("/api/backup/trigger")
async def trigger_manual_backup(req: BackupTriggerRequest, request: Request):
    """Triggers automated backup script execution (requires Master PIN)."""
    check_auth_request(request, req.pin)
    mgr = get_backup_manager()
    result = await mgr.trigger_backup(force=req.force)
    if not result.get("success"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR if result.get("status") == "error" else status.HTTP_400_BAD_REQUEST,
            content=result,
        )
    return result


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the dashboard index HTML from compiled Svelte 5 SPA."""
    dist_index = FRONTEND_DIST / "index.html"
    if dist_index.is_file():
        return HTMLResponse(content=dist_index.read_text(encoding="utf-8"))

    # Fallback placeholder HTML if frontend has not been compiled yet
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
    <p>Backend API Engine & Power Bridge active (Phases 1 & 2 Ready).</p>
    <p>Inspect live endpoints: <a href="/docs">Swagger API Docs</a> | <a href="/api/stats/snapshot">Stats Snapshot</a> | <a href="/api/power/status">Power Status</a></p>
  </div>
</body>
</html>
""")


if __name__ == "__main__":
    import uvicorn
    cfg = get_config()
    uvicorn.run("src.main:app", host=cfg.server.host, port=cfg.server.port, reload=True)
