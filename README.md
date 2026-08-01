# AutoExplain AI — Vehicle Health Copilot

> "Understand Your Vehicle. Not Just Your Bill."

AutoExplain AI turns confusing vehicle service, inspection, and diagnostic
reports into plain-English explanations: what's wrong, how urgent it is,
what it should cost, and what happens if you ignore it.

This is **not** a replacement for a mechanic. It's an explanation layer on
top of the report a mechanic already gave you.

## Status: Slice 2 (in progress)

Slice 1 proved the core pipeline. Slice 2 adds what's needed to actually
use it day-to-day: multiple vehicles per user, persisted report history,
a lightweight static frontend, and a "virtual mechanic" chat grounded in
each vehicle's latest report.

**New in Slice 2:**

- **Vehicles**: create/list/delete, each owned by a user. `POST/GET /api/v1/vehicles`
- **Persistence**: SQLite by default (zero setup — a file, not a server). Every analyzed report is saved against a vehicle. `GET /api/v1/vehicles/{id}/reports` for history, `GET /api/v1/reports/{id}` for a specific one.
- **Auth-lite**: no login system yet. The frontend generates a random device ID (stored in `localStorage`) sent as `X-User-Id` on every request; the backend creates a `User` row for it on first sight. This is what makes "each user has their own vehicles" work without building email/Google login under time pressure — see `app/api/deps.py` for exactly what this does and doesn't guarantee (no password, no real identity verification). Swapping in real auth later replaces only that one function.
- **Virtual mechanic chat**: `POST /api/v1/chat`. If a vehicle has an analyzed report, answers are grounded in its actual findings; otherwise it answers as general automotive knowledge and says so.
- **Frontend**: `frontend/index.html` — a single static file, vanilla JS, talks directly to the FastAPI backend. No Next.js, no Node, no build step — open it in a browser. This was a deliberate scope cut for speed; migrating to the Next.js frontend from the original spec is a later, non-urgent step and won't require backend changes.

### Running Slice 2

Backend: same as Slice 1 setup, then:
```bash
uvicorn app.main:app --reload
```
A `autoexplain.db` SQLite file will be created automatically on first run.

Frontend: just open `frontend/index.html` directly in a browser (double-click it, or File → Open). It expects the backend running at `http://localhost:8000`.

### Known scope cuts (be aware of these)

- No real authentication — anyone with a device ID can act as that user. Fine for personal/demo use, not for a public multi-user launch.
- No rate limiting or upload size enforcement beyond the config value.
- CORS is wide open (`allow_origins=["*"]`) — fine for local dev, must be tightened before any public deployment.
- Chat has no persistence — history resets on page reload.

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
│   │   │   ├── config.py           # settings, env vars
│   │   │   └── db.py               # SQLAlchemy engine/session (SQLite by default)
│   │   ├── models/
│   │   │   └── orm.py              # User, Vehicle, Report tables
│   │   ├── schemas/
│   │   │   ├── report.py           # Pydantic models — the extraction contract
│   │   │   ├── vehicle.py
│   │   │   └── chat.py
│   │   ├── services/
│   │   │   ├── ocr_service.py      # PDF/image -> raw text
│   │   │   ├── llm_provider.py     # interchangeable LLM backend (OpenAI/Anthropic)
│   │   │   ├── extraction_service.py   # raw text -> structured JSON
│   │   │   ├── severity_service.py     # issue -> severity + risk score
│   │   │   ├── rag_cost_service.py     # issue -> grounded cost range
│   │   │   ├── explanation_service.py  # issue -> plain-English explanation
│   │   │   └── chat_service.py         # virtual mechanic, report-grounded
│   │   ├── api/
│   │   │   ├── deps.py             # device-ID auth-lite (see Slice 2 notes below)
│   │   │   └── v1/endpoints/
│   │   │       ├── reports.py      # POST /reports/analyze, GET /reports/{id}
│   │   │       ├── vehicles.py     # vehicle CRUD, report history
│   │   │       └── chat.py         # POST /chat
│   │   └── pipeline.py             # wires OCR/extraction/explanation into one call
│   ├── requirements.txt
│   ├── .env.example
│   └── tests/
├── frontend/
│   └── index.html                  # static, vanilla JS — see Slice 2 notes below
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

- **Slice 3:** Real authentication (email/Google login) replacing the device-ID stand-in
- **Slice 4:** Vehicle health score, maintenance timeline, repair prioritization
- **Slice 5:** Migrate frontend to Next.js (from the static HTML) once product direction stabilizes
- **Slice 6+:** Dashboard warning-light detection, OBD-II ingestion, fleet/insurance roles

## Disclaimer

AutoExplain AI provides informational explanations of third-party
inspection/service reports. It is not a substitute for professional
mechanical inspection or advice. Always consult a qualified mechanic
before making repair decisions, especially for anything flagged as
high urgency or safety-related.
