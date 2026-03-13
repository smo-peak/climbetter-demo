import time
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from app.database import get_pool

router = APIRouter(prefix="/api/v1", tags=["waitlist"])

# Simple in-memory rate limiting: {ip: [timestamps]}
_rate_limits: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 5
_RATE_WINDOW = 60  # seconds


class WaitlistRequest(BaseModel):
    email: EmailStr


@router.post("/waitlist")
async def join_waitlist(body: WaitlistRequest, request: Request):
    # Rate limiting
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _rate_limits[ip] = [t for t in _rate_limits[ip] if now - t < _RATE_WINDOW]
    if len(_rate_limits[ip]) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests")
    _rate_limits[ip].append(now)

    pool = get_pool()
    await pool.execute(
        """
        INSERT INTO waitlist (email, source)
        VALUES ($1, 'landing')
        ON CONFLICT (email) DO NOTHING
        """,
        body.email,
    )
    return {"status": "ok", "message": "Bienvenue ! Tu seras parmi les premiers."}
