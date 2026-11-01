"""Database CRUD operations for services."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import delete, distinct, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Service

logger = logging.getLogger("janus.db.crud")


async def get_all_services(
    session: AsyncSession,
    category: Optional[str] = None,
    enabled_only: bool = True,
) -> List[Service]:
    """Retrieves services ordered by category and display order."""
    query = select(Service)
    if enabled_only:
        query = query.where(Service.is_enabled.is_(True))
    if category:
        query = query.where(Service.category == category)
    query = query.order_by(Service.category.asc(), Service.display_order.asc(), Service.name.asc())

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_service_by_id(session: AsyncSession, service_id: str) -> Optional[Service]:
    """Retrieves a single service by UUID primary key."""
    result = await session.execute(select(Service).where(Service.id == service_id))
    return result.scalar_one_or_none()


async def create_service(session: AsyncSession, data: Dict[str, Any]) -> Service:
    """Inserts a new service into the database."""
    item_id = data.get("id") or str(uuid.uuid4())
    svc = Service(
        id=item_id,
        name=data["name"].strip(),
        category=data["category"].strip(),
        url=data["url"].strip(),
        external_url=data.get("external_url", "").strip() or None if data.get("external_url") else None,
        health_check_url=data.get("health_check_url", "").strip() or None if data.get("health_check_url") else None,
        icon=data.get("icon", "globe").strip() or "globe",
        description=data.get("description", "").strip() or None if data.get("description") else None,
        display_order=data.get("display_order", 0),
        is_enabled=data.get("is_enabled", True),
    )
    session.add(svc)
    await session.flush()
    await session.refresh(svc)
    return svc


async def update_service(session: AsyncSession, service_id: str, data: Dict[str, Any]) -> Optional[Service]:
    """Updates an existing service."""
    svc = await get_service_by_id(session, service_id)
    if not svc:
        return None

    if "name" in data and data["name"] is not None:
        svc.name = data["name"].strip()
    if "category" in data and data["category"] is not None:
        svc.category = data["category"].strip()
    if "url" in data and data["url"] is not None:
        svc.url = data["url"].strip()
    if "external_url" in data:
        svc.external_url = data["external_url"].strip() or None if data["external_url"] else None
    if "health_check_url" in data:
        svc.health_check_url = data["health_check_url"].strip() or None if data["health_check_url"] else None
    if "icon" in data and data["icon"] is not None:
        svc.icon = data["icon"].strip() or "globe"
    if "description" in data:
        svc.description = data["description"].strip() or None if data["description"] else None
    if "display_order" in data and data["display_order"] is not None:
        svc.display_order = data["display_order"]
    if "is_enabled" in data and data["is_enabled"] is not None:
        svc.is_enabled = data["is_enabled"]

    await session.flush()
    await session.refresh(svc)
    return svc


async def delete_service(session: AsyncSession, service_id: str) -> bool:
    """Deletes a service by UUID."""
    svc = await get_service_by_id(session, service_id)
    if not svc:
        return False
    await session.delete(svc)
    await session.flush()
    return True


async def reorder_services(session: AsyncSession, orders: List[Dict[str, Any]]) -> bool:
    """Updates display_order for multiple services."""
    for item in orders:
        svc_id = item.get("id")
        order = item.get("display_order", 0)
        if svc_id:
            await session.execute(
                update(Service).where(Service.id == svc_id).values(display_order=order)
            )
    await session.flush()
    return True


async def get_distinct_categories(session: AsyncSession) -> List[str]:
    """Returns a list of all distinct category names in use."""
    result = await session.execute(
        select(distinct(Service.category)).where(Service.is_enabled.is_(True)).order_by(Service.category.asc())
    )
    return [row[0] for row in result.all() if row[0]]
