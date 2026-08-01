from app.schemas.report import (
    AnalyzedReport,
    CostEstimate,
    ExplainedIssue,
    ExtractedReport,
    Severity,
    VehicleInfo,
)


def test_extracted_report_allows_empty_issues():
    report = ExtractedReport(vehicle=VehicleInfo(), extraction_confidence=0.8)
    assert report.issues == []


def test_explained_issue_requires_severity_and_risk_score():
    issue = ExplainedIssue(
        title="Brake pad worn",
        meaning="Your brake pads are thin and need replacing soon.",
        why_it_happens="Normal wear from braking over time.",
        severity=Severity.RED,
        risk_score=85,
        can_it_wait=False,
        urgency_note="Replace within a few days.",
        estimated_cost=CostEstimate(low=1500, high=4500, grounded=True),
    )
    assert issue.severity == Severity.RED
    assert 0 <= issue.risk_score <= 100


def test_analyzed_report_has_default_disclaimer():
    report = AnalyzedReport(
        vehicle=VehicleInfo(),
        report_date=None,
        service_center=None,
        issues=[],
        overall_summary="No issues found.",
        extraction_confidence=0.9,
    )
    assert "not a substitute" in report.disclaimer.lower()
