"""
Auth-lite: identify "who's asking" without a login system.

The frontend generates a random device ID once (localStorage) and sends
it as X-User-Id on every request. First time we see an ID, we create a
User row for it. This is intentionally not real auth -- no password, no
verification, anyone who copies the header can act as that user -- but
it's what makes "each user has their own vehicles" work without
building email/Google login under time pressure.

Swapping to real auth later means replacing ONLY this function's
internals (verify a JWT / session instead of trusting a raw header) --
every endpoint that depends on get_current_user stays unchanged.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.orm import User


def get_current_user(
    x_user_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")

    user = db.get(User, x_user_id)
    if user is None:
        user = User(id=x_user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
