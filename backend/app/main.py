from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import chat, reports, vehicles
from app.core.config import get_settings
from app.core.db import init_db

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Understand Your Vehicle. Not Just Your Bill.",
    version="0.2.0-slice2",
)

# The frontend is a static file opened directly in a browser (no dev
# server, no fixed origin) -- open CORS for now. Tighten to a specific
# origin once this is deployed somewhere with a real domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vehicles.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}
