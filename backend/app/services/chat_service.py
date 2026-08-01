"""
Virtual mechanic: conversational Q&A, optionally grounded in a specific
vehicle's most recent analyzed report.

Two modes, decided automatically:
  - Grounded: vehicle_id given AND that vehicle has at least one report
    -> the report's issues/costs/severities are injected as context,
    answers reference this vehicle's actual findings.
  - General: no vehicle, or a vehicle with no reports yet -> answers
    general vehicle-care questions honestly as general knowledge, and
    says so, rather than pretending to know this car's specific state.

This distinction matters for trust: a user should always be able to
tell whether "yes, safe to drive short distances" is about their exact
brake pad reading or is generic advice.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.orm import Report as ReportModel
from app.models.orm import Vehicle
from app.services.llm_provider import LLMProvider

_BASE_SYSTEM_PROMPT = """You are AutoExplain AI's virtual mechanic. You \
explain vehicle issues in plain English to people with zero mechanical \
knowledge -- think of explaining a medical report to a worried patient, \
not talking to another mechanic.

Rules:
- Never invent specifics (costs, part names, diagnoses) that aren't in \
the provided context or general automotive knowledge.
- For anything safety-relevant or where you're genuinely uncertain, \
recommend an in-person inspection rather than giving a definitive \
verdict. You are informational support, not a replacement for a \
qualified mechanic.
- Keep answers focused and conversational -- a few sentences, not an \
essay, unless the question genuinely needs more.
- If asked something outside vehicles/automotive topics, politely \
redirect -- you're a vehicle assistant, not a general chatbot."""


class ChatService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def reply(
        self,
        db: Session,
        vehicle_id: str | None,
        message: str,
        history: list[dict[str, str]],
    ) -> tuple[str, bool]:
        system_prompt, grounded = self._build_system_prompt(db, vehicle_id)

        messages = [*history, {"role": "user", "content": message}]
        reply_text = self._llm.complete_text(system_prompt, messages)
        return reply_text, grounded

    def _build_system_prompt(
        self, db: Session, vehicle_id: str | None
    ) -> tuple[str, bool]:
        if not vehicle_id:
            return self._general_prompt(), False

        vehicle = db.get(Vehicle, vehicle_id)
        if vehicle is None or not vehicle.reports:
            return self._general_prompt(vehicle), False

        latest_report: ReportModel = vehicle.reports[0]  # ordered desc in relationship
        report_data = json.loads(latest_report.analyzed_json)

        context = f"""
VEHICLE: {vehicle.year or ""} {vehicle.make} {vehicle.model}
LATEST REPORT SUMMARY: {report_data.get("overall_summary", "")}

KNOWN ISSUES FROM THIS REPORT:
{json.dumps(report_data.get("issues", []), indent=2)}

Ground your answers in this specific vehicle's actual findings above \
when the question relates to them. Be explicit when you're answering \
from this report vs. general knowledge."""

        return _BASE_SYSTEM_PROMPT + "\n\n" + context, True

    def _general_prompt(self, vehicle: Vehicle | None = None) -> str:
        if vehicle:
            note = (
                f"\n\nThe user's vehicle on file is a {vehicle.year or ''} "
                f"{vehicle.make} {vehicle.model}, but it has no analyzed "
                "report yet -- answer generally and mention that uploading "
                "a report would let you give vehicle-specific answers."
            )
        else:
            note = "\n\nNo specific vehicle is selected -- answer generally."
        return _BASE_SYSTEM_PROMPT + note
