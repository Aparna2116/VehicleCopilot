from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import reports
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Understand Your Vehicle. Not Just Your Bill.",
    version="0.1.0-slice1",
)

# Slice 1 has no frontend deployed yet -- open CORS for local dev.
# Tighten this to the actual frontend origin before Slice 3.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}
