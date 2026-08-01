from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import get_settings
from app.pipeline import AnalysisPipeline
from app.schemas.report import AnalyzedReport

router = APIRouter(prefix="/reports", tags=["reports"])
settings = get_settings()

# One pipeline instance per process is fine for Slice 1 (single-worker
# dev usage). Move to a request-scoped or pooled dependency once this
# is behind real concurrent traffic.
_pipeline = AnalysisPipeline()


@router.post("/analyze", response_model=AnalyzedReport)
async def analyze_report(file: UploadFile = File(...)) -> AnalyzedReport:
    _validate_file(file)
    file_bytes = await file.read()

    try:
        return _pipeline.run(file_bytes, file.filename)
    except ValueError as exc:
        # Raised by llm_provider._safe_json_parse on malformed LLM output
        raise HTTPException(status_code=502, detail=str(exc)) from exc


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
