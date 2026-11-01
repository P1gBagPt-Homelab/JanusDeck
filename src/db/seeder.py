"""Automatic initial data seeder for JanusDeck PostgreSQL database."""

from __future__ import annotations

import logging
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import AppConfig
from src.db.models import Service

logger = logging.getLogger("janus.db.seeder")


async def seed_services_from_config_if_empty(session: AsyncSession, config: AppConfig) -> int:
    """Imports initial services from config.yaml into PostgreSQL if the table is empty."""
    if not config.services:
        return 0

    count_result = await session.execute(select(func.count(Service.id)))
    count = count_result.scalar_one() or 0

    if count > 0:
        logger.debug("Database already contains %d services. Skipping seeder.", count)
        return 0

    logger.info("Database contains 0 services. Seeding initial services from configuration...")
    seeded_count = 0

    for category_block in config.services:
        cat_name = category_block.category.strip()
        for idx, item in enumerate(category_block.items):
            svc = Service(
                id=item.id or str(uuid.uuid4()),
                name=item.name.strip(),
                category=cat_name,
                url=item.url.strip(),
                external_url=item.external_url.strip() if item.external_url else None,
                health_check_url=item.health_check_url.strip() if item.health_check_url else None,
                icon=item.icon.strip() if item.icon else "globe",
                description=item.description.strip() if item.description else None,
                display_order=item.display_order if item.display_order else idx,
                is_enabled=item.is_enabled,
            )
            session.add(svc)
            seeded_count += 1

    await session.commit()
    logger.info("Successfully seeded %d homelab services into PostgreSQL.", seeded_count)
    return seeded_count
