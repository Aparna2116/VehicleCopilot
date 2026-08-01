"""
Structured extraction: raw OCR text -> ExtractedReport.

This is layout-agnostic by design: rather than templating against a
specific garage's report format, we give the LLM the fixed target schema
and let it map whatever layout it sees onto that schema. If the OCR text
is noisy, extraction_confidence should reflect that — this is a
self-reported signal from the model, surfaced to the user rather than
hidden.
"""
from __future__ import annotations

from app.schemas.report import ExtractedReport
from app.services.llm_provider import LLMProvider

_SYSTEM_PROMPT = """You are an expert at reading vehicle service, \
inspection, and diagnostic reports and converting them into structured \
data. Reports come from many different garages with different formats \
-- extract the meaning, not the layout.

Rules:
- Never invent data. If a field isn't present in the text, leave it null.
- Each distinct problem/finding becomes one entry in `issues`. Do not \
merge unrelated issues, and do not split one issue into several.
- `technician_remark` should stay close to the original wording found \
in the text, not paraphrased.
- `extraction_confidence` (0-1) should reflect how confident you are \
in this extraction given the input text quality -- lower it if the \
OCR text looks garbled, truncated, or ambiguous.
- Output must match the given JSON schema exactly."""


class ExtractionService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def extract(self, ocr_text: str, ocr_confidence: float) -> ExtractedReport:
        user_prompt = f"""Extract this vehicle report into the schema below.

TARGET SCHEMA:
{ExtractedReport.model_json_schema()}

OCR CONFIDENCE OF THE SOURCE TEXT: {ocr_confidence:.2f} (factor this into \
your own extraction_confidence -- extraction can't be more reliable than \
the text it's reading from)

REPORT TEXT:
{ocr_text}
"""
        raw = self._llm.complete_json(_SYSTEM_PROMPT, user_prompt)
        return ExtractedReport.model_validate(raw)
