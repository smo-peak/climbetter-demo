from fastapi import APIRouter

from app.database import get_pool

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck():
    pool = get_pool()
    async with pool.acquire() as conn:
        db_ok = await conn.fetchval("SELECT 1") == 1
    return {"status": "ok", "database": db_ok}
