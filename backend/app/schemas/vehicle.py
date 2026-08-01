from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class VehicleCreate(BaseModel):
    nickname: str | None = None
    make: str
    model: str
    year: int | None = None
    registration_number: str | None = None


class VehicleOut(BaseModel):
    id: str
    nickname: str | None
    make: str
    model: str
    year: int | None
    registration_number: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportSummary(BaseModel):
    """Lightweight view for report history lists -- full detail comes
    from re-fetching /reports/{id}, not from this summary."""

    id: str
    filename: str | None
    overall_summary: str
    red_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
