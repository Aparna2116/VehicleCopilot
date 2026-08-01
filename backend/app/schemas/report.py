"""
The extraction contract.

Every service report — no matter which garage's letterhead it has — gets
normalized into this fixed shape. This is what makes layout-agnostic
extraction possible: the LLM's job is always "fill in this schema", not
"figure out this specific template".
"""
from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"


class VehicleInfo(BaseModel):
    make: str | None = None
    model: str | None = None
    year: int | None = None
    vin: str | None = None
    mileage_km: int | None = None
    registration_number: str | None = None


class RawIssue(BaseModel):
    """An issue as extracted from the report, before explanation/severity."""
    title: str = Field(..., description="Short name, e.g. 'Brake pad worn'")
    technician_remark: str | None = Field(
        None, description="Verbatim or near-verbatim technician note, if present"
    )
    component: str | None = Field(None, description="e.g. 'brakes', 'suspension', 'engine'")
    diagnostic_code: str | None = Field(None, description="e.g. 'P0420', if applicable")


class LineItem(BaseModel):
    description: str
    part_or_labor: str | None = None  # "part" | "labor" | "tax" | "fee"
    amount: float | None = None


class ExtractedReport(BaseModel):
    """Output of OCR + extraction — before explanation/severity/cost enrichment."""
    vehicle: VehicleInfo
    report_date: str | None = None
    service_center: str | None = None
    issues: list[RawIssue] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    line_items: list[LineItem] = Field(default_factory=list)
    extraction_confidence: float = Field(
        ..., ge=0, le=1, description="Model's self-assessed extraction confidence"
    )


class CostEstimate(BaseModel):
    low: float | None = None
    high: float | None = None
    currency: str = "INR"
    grounded: bool = Field(
        ..., description="True only if pulled from the cost-reference corpus via RAG"
    )
    source_note: str | None = None


class ExplainedIssue(BaseModel):
    """A single issue, fully enriched — this is what the user actually reads."""
    title: str
    meaning: str = Field(..., description="Plain-English explanation, zero jargon assumed")
    why_it_happens: str
    symptoms: list[str] = Field(default_factory=list)
    if_ignored: list[str] = Field(default_factory=list)
    severity: Severity
    risk_score: int = Field(..., ge=0, le=100)
    can_it_wait: bool
    urgency_note: str
    estimated_cost: CostEstimate
    preventive_tips: list[str] = Field(default_factory=list)


class AnalyzedReport(BaseModel):
    """Final pipeline output returned to the client."""
    vehicle: VehicleInfo
    report_date: str | None
    service_center: str | None
    issues: list[ExplainedIssue]
    overall_summary: str
    extraction_confidence: float
    disclaimer: str = (
        "This is an informational explanation of your report, not a "
        "substitute for professional mechanical advice. Consult a "
        "qualified mechanic before making repair decisions."
    )
