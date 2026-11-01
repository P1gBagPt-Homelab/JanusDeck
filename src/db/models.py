"""SQLAlchemy database models for JanusDeck."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Service(Base):
    __tablename__ = "services"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    external_url = Column(String(500), nullable=True)
    health_check_url = Column(String(500), nullable=True)
    icon = Column(String(50), nullable=False, default="globe")
    description = Column(String(255), nullable=True)
    display_order = Column(Integer, nullable=False, default=0, index=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "url": self.url,
            "external_url": self.external_url,
            "health_check_url": self.health_check_url,
            "icon": self.icon,
            "description": self.description,
            "display_order": self.display_order,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
