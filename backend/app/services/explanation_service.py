"""
Per-issue explanation and severity scoring.

One LLM call per issue produces the full ExplainedIssue (meaning,
severity, symptoms, etc.) EXCEPT the cost estimate, which is grounded
separately via RAGCostService and merged in afterward. Keeping cost
generation out of this prompt is deliberate -- see rag_cost_service.py
for why.
"""
from __future__ import annotations

from app.schemas.report import CostEstimate, ExplainedIssue, RawIssue, Severity
from app.services.llm_provider import LLMProvider
from app.services.rag_cost_service import RAGCostService

_SYSTEM_PROMPT = """You are AutoExplain AI, explaining a vehicle repair \
finding to someone with zero mechanical knowledge -- imagine explaining \
a medical report to a worried patient. Never use unexplained jargon: if \
you must use a technical term, define it in the same sentence.

For the given issue, produce:
- meaning: what this actually means, in plain English, 1-2 sentences
- why_it_happens: brief, plain-English cause
- symptoms: what the driver might notice (list; empty list if none obvious)
- if_ignored: concrete consequences of not fixing this (list)
- severity: one of "green" (informational/cosmetic), "yellow" (schedule \
soon), "orange" (schedule promptly), "red" (safety-relevant, urgent)
- risk_score: 0-100, consistent with the severity level
- can_it_wait: true/false
- urgency_note: one sentence, direct guidance on timing
- preventive_tips: how to avoid this recurring (list; empty if not applicable)

Be honest and calibrated -- do not inflate urgency to seem thorough, and \
do not downplay genuine safety issues. Output must match the given JSON \
schema exactly, with no `estimated_cost` field (that is added separately)."""


class ExplanationService:
    def __init__(self, llm: LLMProvider, rag: RAGCostService) -> None:
        self._llm = llm
        self._rag = rag

    def explain(self, issue: RawIssue) -> ExplainedIssue:
        schema = ExplainedIssue.model_json_schema()
        schema["properties"].pop("estimated_cost", None)

        user_prompt = f"""Issue to explain:
Title: {issue.title}
Component: {issue.component or "unknown"}
Diagnostic code: {issue.diagnostic_code or "none"}
Technician remark: {issue.technician_remark or "none provided"}

TARGET SCHEMA (excluding estimated_cost, added separately):
{schema}
"""
        raw = self._llm.complete_json(_SYSTEM_PROMPT, user_prompt)
        raw["estimated_cost"] = self._ground_cost(issue).model_dump()
        return ExplainedIssue.model_validate(raw)

    # ---- cost grounding --------------------------------------------------

    def _ground_cost(self, issue: RawIssue) -> CostEstimate:
        query = f"{issue.title} {issue.component or ''} {issue.diagnostic_code or ''}"
        # top_k=3: retrieval often splits "what this means" (urgency notes)
        # from "what it costs" (the numeric section) across chunks -- see
        # rag_cost_service.py test findings. A wider net makes it more
        # likely the actual $ figures are included alongside the context.
        chunks = self._rag.retrieve(query, top_k=3)

        if not chunks:
            return CostEstimate(
                low=None,
                high=None,
                grounded=False,
                source_note="No matching reference data found for this issue yet.",
            )

        # Concatenate all retrieved chunks, not just the top one: the
        # highest-scoring chunk (e.g. an "urgency notes" section) often
        # discusses the issue without containing the actual $ figures,
        # which may sit in a sibling chunk from the same source file.
        reference_text = "\n\n".join(
            f"[{c.heading}]\n{c.text}" for c in chunks
        )

        extraction_prompt = f"""From the reference text below, extract a \
typical repair cost range in INR for: "{issue.title}".

If the text gives a specific numeric range, use it. If it only covers a \
related but different job, say so honestly rather than forcing a number.

REFERENCE TEXT:
{reference_text}

Respond as JSON: {{"low": number or null, "high": number or null, \
"source_note": "one sentence on what this range covers"}}"""

        result = self._llm.complete_json(
            "You extract numeric cost ranges from reference text. Never "
            "invent numbers not present in the text.",
            extraction_prompt,
        )
        return CostEstimate(
            low=result.get("low"),
            high=result.get("high"),
            grounded=True,
            source_note=result.get("source_note"),
        )
