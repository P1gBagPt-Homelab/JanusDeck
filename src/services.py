"""Service directory and health evaluation for JanusDeck."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List
import httpx

from src.config import AppConfig, ServiceCategory, ServiceItem, get_config

logger = logging.getLogger("janus.services")


async def ping_service(item: ServiceItem, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Evaluates the reachability and response latency of a single service."""
    target_url = item.health_check_url or item.url
    start_time = time.perf_counter()

    result: Dict[str, Any] = {
        "name": item.name,
        "url": item.url,
        "external_url": item.external_url,
        "icon": item.icon,
        "description": item.description,
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


async def check_all_services(config: AppConfig, timeout_seconds: float = 3.0) -> List[Dict[str, Any]]:
    """Checks all services across all categories concurrently."""
    all_categories: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_seconds),
        verify=False,
        follow_redirects=True,
    ) as client:
        for category_block in config.services:
            tasks = [ping_service(item, client) for item in category_block.items]
            items_status = await asyncio.gather(*tasks, return_exceptions=False)
            for itm in items_status:
                itm["category"] = category_block.category
            all_categories.append({
                "category": category_block.category,
                "items": items_status,
            })

    return all_categories
