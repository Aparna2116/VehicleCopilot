# AutoExplain AI — Vehicle Health Copilot

> "Understand Your Vehicle. Not Just Your Bill."

AutoExplain AI turns confusing vehicle service, inspection, and diagnostic
reports into plain-English explanations: what's wrong, how urgent it is,
what it should cost, and what happens if you ignore it.

This is **not** a replacement for a mechanic. It's an explanation layer on
top of the report a mechanic already gave you.

## Status: Slice 1 (in progress)

We're building this in slices, proving the riskiest part first before
layering on auth, a frontend, and the rest of the product surface.

**Slice 1 scope — the core pipeline, backend-only:**

```
Upload report (PDF/image)
    ↓
OCR (Tesseract, PaddleOCR planned as swap-in)
    ↓
LLM structured extraction → fixed Pydantic schema
    ↓
Per-issue LLM explanation (meaning, urgency, symptoms, consequences)
    ↓
Severity scoring (Green/Yellow/Orange/Red + 0-100 risk score)
    ↓
Cost-range grounding via RAG (pgvector) over a curated cost-reference corpus
    ↓
Structured JSON response
```

No auth, no database persistence, no frontend yet — those are later slices.
The goal right now is: can we reliably turn a messy real-world report into
accurate, trustworthy, well-grounded explanations?

**Deliberately out of scope for Slice 1:** dashboard warning-light image
detection, OBD-II Bluetooth ingestion, invoice fraud detection,
multi-tenant fleet/insurance roles. These are real V2+ features, not V1.

## Why RAG for cost estimates, not raw LLM output

LLMs will confidently invent a repair cost if you let them. Every cost
range returned by this pipeline is retrieved from the cost-reference
corpus (`data/cost_reference_corpus/`), not generated freeform. If the
corpus has no relevant entry, the API says so explicitly rather than
guessing — see `RAGCostService` in the backend.

## Project layout

```
VehicleCopilot/
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entrypoint
│   │   ├── core/
│   │   │   └── config.py           # settings, env vars
│   │   ├── schemas/
│   │   │   └── report.py           # Pydantic models — the extraction contract
│   │   ├── services/
│   │   │   ├── ocr_service.py      # PDF/image -> raw text
│   │   │   ├── llm_provider.py     # interchangeable LLM backend (OpenAI/Anthropic)
│   │   │   ├── extraction_service.py   # raw text -> structured JSON
│   │   │   ├── severity_service.py     # issue -> severity + risk score
│   │   │   ├── rag_cost_service.py     # issue -> grounded cost range
│   │   │   └── explanation_service.py  # issue -> plain-English explanation
│   │   ├── api/v1/endpoints/
│   │   │   └── reports.py          # POST /api/v1/reports/analyze
│   │   └── pipeline.py             # wires the above into one call
│   ├── requirements.txt
│   ├── .env.example
│   └── tests/
└── data/
    └── cost_reference_corpus/      # seed corpus for RAG cost grounding
```

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

# System dependency: Tesseract OCR must be installed separately
#   macOS:   brew install tesseract poppler
#   Ubuntu:  sudo apt install tesseract-ocr poppler-utils
#   Windows: https://github.com/UB-Mannheim/tesseract/wiki

cp .env.example .env
# fill in ANTHROPIC_API_KEY (or OPENAI_API_KEY) and DATABASE_URL

uvicorn app.main:app --reload
```

Then `POST` a report file to `http://localhost:8000/api/v1/reports/analyze`.

## Roadmap (later slices)

- **Slice 2:** Postgres persistence, user accounts, service history
- **Slice 3:** Next.js frontend (upload, analysis view, chat)
- **Slice 4:** AI chat grounded in the specific report
- **Slice 5:** Vehicle health score, maintenance timeline, repair prioritization
- **Slice 6+:** Dashboard warning-light detection, OBD-II ingestion, fleet/insurance roles

## Disclaimer

AutoExplain AI provides informational explanations of third-party
inspection/service reports. It is not a substitute for professional
mechanical inspection or advice. Always consult a qualified mechanic
before making repair decisions, especially for anything flagged as
high urgency or safety-related.
