"""
DB engine + session.

Defaults to a local SQLite file so Slice 2 runs with zero extra setup —
no Postgres install required to try the app. DATABASE_URL in .env can
still point at Postgres for anything closer to production; nothing else
in the codebase needs to change to switch.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Slice 2: create_all is fine for a young schema. Once this needs
    # real migrations (schema changes without dropping data), swap to
    # Alembic -- already in requirements.txt for that reason.
    from app.models import orm  # noqa: F401 (ensures models are registered)

    Base.metadata.create_all(bind=engine)
