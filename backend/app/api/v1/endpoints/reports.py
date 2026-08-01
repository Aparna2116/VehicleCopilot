from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.endpoints.vehicles import _get_owned_vehicle
from app.core.config import get_settings
from app.core.db import get_db
from app.models.orm import Report as ReportModel
from app.models.orm import User
from app.pipeline import AnalysisPipeline
from app.schemas.report import AnalyzedReport

router = APIRouter(prefix="/reports", tags=["reports"])
settings = get_settings()

# One pipeline instance per process is fine for this scale of usage.
# Move to a request-scoped or pooled dependency once behind real
# concurrent traffic.
_pipeline = AnalysisPipeline()


@router.post("/analyze", response_model=AnalyzedReport)
async def analyze_report(
    vehicle_id: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyzedReport:
    vehicle = _get_owned_vehicle(vehicle_id, user, db)
    _validate_file(file)
    file_bytes = await file.read()

    try:
        analyzed = _pipeline.run(file_bytes, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    report_row = ReportModel(
        vehicle_id=vehicle.id,
        filename=file.filename,
        analyzed_json=analyzed.model_dump_json(),
    )
    db.add(report_row)
    db.commit()
    db.refresh(report_row)

    return analyzed


@router.get("/{report_id}", response_model=AnalyzedReport)
def get_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyzedReport:
    report = db.get(ReportModel, report_id)
    if report is None or report.vehicle.user_id != user.id:
        raise HTTPException(status_code=404, detail="Report not found")
    return AnalyzedReport.model_validate(json.loads(report.analyzed_json))


def _validate_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. "
            f"Allowed: {sorted(settings.ALLOWED_EXTENSIONS)}",
        )
