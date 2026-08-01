"""
ORM models.

User is intentionally minimal (id only, no auth fields yet) — Slice 2
identifies "who's asking" via a client-generated device ID sent as a
header, not a login. This is what makes "multiple vehicles per user"
possible without building a full auth system under time pressure. Real
auth (email/Google login, per the original spec) is a drop-in swap
later: the User row already exists, only how it gets identified changes.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="owner")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    nickname: Mapped[str | None] = mapped_column(String, nullable=True)
    make: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    owner: Mapped[User] = relationship(back_populates="vehicles")
    reports: Mapped[list["Report"]] = relationship(
        back_populates="vehicle", order_by="Report.created_at.desc()"
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"))
    filename: Mapped[str | None] = mapped_column(String, nullable=True)
    # Full AnalyzedReport, stored as JSON text -- avoids modeling every
    # nested issue/cost field as its own table for a young schema that's
    # still likely to change shape.
    analyzed_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    vehicle: Mapped[Vehicle] = relationship(back_populates="reports")
