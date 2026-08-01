"""
End-to-end pipeline: uploaded file bytes -> AnalyzedReport.

This is the one place that knows the full sequence. Every stage is
injected as a dependency so each one is independently unit-testable
(e.g. test ExplanationService with a fake LLMProvider that returns
canned JSON, no real API calls needed).
"""
from __future__ import annotations

from app.schemas.report import AnalyzedReport, ExplainedIssue
from app.services.explanation_service import ExplanationService
from app.services.extraction_service import ExtractionService
from app.services.llm_provider import get_llm_provider
from app.services.ocr_service import OCRService
from app.services.rag_cost_service import RAGCostService


class AnalysisPipeline:
    def __init__(self) -> None:
        llm = get_llm_provider()
        self.ocr = OCRService()
        self.extraction = ExtractionService(llm)
        self.explanation = ExplanationService(llm, RAGCostService())

    def run(self, file_bytes: bytes, filename: str) -> AnalyzedReport:
        ocr_result = self.ocr.extract(file_bytes, filename)

        extracted = self.extraction.extract(
            ocr_text=ocr_result.text,
            ocr_confidence=ocr_result.mean_confidence,
        )

        explained_issues: list[ExplainedIssue] = [
            self.explanation.explain(issue) for issue in extracted.issues
        ]

        return AnalyzedReport(
            vehicle=extracted.vehicle,
            report_date=extracted.report_date,
            service_center=extracted.service_center,
            issues=explained_issues,
            overall_summary=self._summarize(explained_issues),
            extraction_confidence=extracted.extraction_confidence,
        )

    def _summarize(self, issues: list[ExplainedIssue]) -> str:
        if not issues:
            return "No issues were detected in this report."

        red_count = sum(1 for i in issues if i.severity.value == "red")
        if red_count:
            return (
                f"{len(issues)} issue(s) found, including {red_count} "
                "marked urgent/safety-relevant. Review those first."
            )
        return f"{len(issues)} issue(s) found. None flagged as urgent."
