"""Service directory and health evaluation for JanusDeck."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Union
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import AppConfig, ServiceCategory, ServiceItem, get_config
from src.db.crud import get_all_services
from src.db.models import Service

logger = logging.getLogger("janus.services")


async def ping_service(item: Union[Service, ServiceItem, Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
    """Evaluates the reachability and response latency of a single service."""
    if isinstance(item, dict):
        name = item.get("name", "Unknown")
        url = item.get("url", "")
        item_id = item.get("id")
        external_url = item.get("external_url")
        icon = item.get("icon") or "globe"
        description = item.get("description")
        health_check_url = item.get("health_check_url")
        category = item.get("category")
        display_order = item.get("display_order", 0)
    else:
        name = getattr(item, "name", "Unknown")
        url = getattr(item, "url", "")
        item_id = getattr(item, "id", None)
        external_url = getattr(item, "external_url", None)
        icon = getattr(item, "icon", "globe") or "globe"
        description = getattr(item, "description", None)
        health_check_url = getattr(item, "health_check_url", None)
        category = getattr(item, "category", None)
        display_order = getattr(item, "display_order", 0)

    target_url = health_check_url or url
    start_time = time.perf_counter()

    result: Dict[str, Any] = {
        "id": item_id,
        "name": name,
        "url": url,
        "external_url": external_url,
        "icon": icon,
        "description": description,
        "category": category,
        "display_order": display_order,
        "health_check_url": target_url,
        "status": "offline",
        "online": False,
        "status_code": None,
        "latency_ms": None,
        "response_time_ms": None,
        "last_checked": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }

    try:
        response = await client.get(target_url)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
        result["latency_ms"] = elapsed_ms
        result["response_time_ms"] = elapsed_ms
        result["status_code"] = response.status_code

        if 200 <= response.status_code < 400:
            result["status"] = "online"
            result["online"] = True
        else:
            result["status"] = "degraded"
            result["online"] = False
            result["error"] = f"HTTP {response.status_code}"
    except httpx.TimeoutException:
        result["status"] = "offline"
        result["online"] = False
        result["error"] = "Connection timed out"
    except httpx.ConnectError:
        result["status"] = "offline"
        result["online"] = False
        result["error"] = "Host unreachable / Connection refused"
    except Exception as exc:
        result["status"] = "offline"
        result["online"] = False
        result["error"] = str(exc)

    return result


async def check_all_services(
    config: Optional[AppConfig] = None,
    session: Optional[AsyncSession] = None,
    timeout_seconds: float = 3.0,
) -> List[Dict[str, Any]]:
    """Checks all services across all categories concurrently.

    If an active database session is provided and database records exist,
    checks services from the database. Otherwise falls back to config.yaml.
    """
    cfg = config or get_config()
    db_services: List[Service] = []

    if session is not None:
        try:
            db_services = await get_all_services(session)
        except Exception as exc:
            logger.warning("Could not fetch services from database: %s", exc)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_seconds),
        verify=False,
        follow_redirects=True,
    ) as client:
        if db_services:
            tasks = [ping_service(svc, client) for svc in db_services]
            items_status = await asyncio.gather(*tasks, return_exceptions=False)

            category_map: Dict[str, List[Dict[str, Any]]] = {}
            for item in items_status:
                cat = item.get("category") or "General"
                if cat not in category_map:
                    category_map[cat] = []
                category_map[cat].append(item)

            return [
                {"category": cat_name, "items": items}
                for cat_name, items in category_map.items()
            ]

        # Fallback to static configuration blocks
        all_categories: List[Dict[str, Any]] = []
        for category_block in cfg.services:
            tasks = [ping_service(item, client) for item in category_block.items]
            items_status = await asyncio.gather(*tasks, return_exceptions=False)
            for itm in items_status:
                itm["category"] = category_block.category
            all_categories.append({
                "category": category_block.category,
                "items": items_status,
            })

        return all_categories
