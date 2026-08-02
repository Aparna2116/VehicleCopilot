from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.orm import User, Vehicle
from app.schemas.vehicle import ReportSummary, VehicleCreate, VehicleOut

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.post("", response_model=VehicleOut)
def create_vehicle(
    payload: VehicleCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Vehicle:
    vehicle = Vehicle(user_id=user.id, **payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("", response_model=list[VehicleOut])
def list_vehicles(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Vehicle]:
    return (
        db.query(Vehicle)
        .filter(Vehicle.user_id == user.id)
        .order_by(Vehicle.created_at.desc())
        .all()
    )


@router.delete("/{vehicle_id}", status_code=204, response_model=None)
def delete_vehicle(
    vehicle_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vehicle = _get_owned_vehicle(vehicle_id, user, db)
    db.delete(vehicle)
    db.commit()


@router.get("/{vehicle_id}/reports", response_model=list[ReportSummary])
def list_vehicle_reports(
    vehicle_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReportSummary]:
    vehicle = _get_owned_vehicle(vehicle_id, user, db)

    summaries = []
    for report in vehicle.reports:
        data = json.loads(report.analyzed_json)
        red_count = sum(1 for i in data.get("issues", []) if i.get("severity") == "red")
        summaries.append(
            ReportSummary(
                id=report.id,
                filename=report.filename,
                overall_summary=data.get("overall_summary", ""),
                red_count=red_count,
                created_at=report.created_at,
            )
        )
    return summaries


def _get_owned_vehicle(vehicle_id: str, user: User, db: Session) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.user_id != user.id:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle
