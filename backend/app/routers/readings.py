from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_user_id
from app.database import get_pool
from app.models.force_readings import ForceReadingBatch, ForceReadingResponse

router = APIRouter(prefix="/api/v1/sessions", tags=["readings"])


@router.post("/{session_id}/readings", status_code=201)
async def ingest_readings(
    session_id: UUID, body: ForceReadingBatch, user_id: str = Depends(get_user_id)
):
    if body.session_id != session_id:
        raise HTTPException(status_code=400, detail="session_id mismatch")

    pool = get_pool()

    owner = await pool.fetchval(
        "SELECT user_id FROM sessions WHERE id = $1 AND status = 'active' AND deleted_at IS NULL",
        session_id,
    )
    if owner is None:
        raise HTTPException(status_code=404, detail="Active session not found")
    if str(owner) != user_id:
        raise HTTPException(status_code=403, detail="Not your session")

    await pool.executemany(
        """
        INSERT INTO force_readings (time, session_id, sensor_position, force_kg, rfd_kgs, quality)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        [
            (r.time, session_id, r.sensor_position, r.force_kg, r.rfd_kgs, r.quality)
            for r in body.readings
        ],
    )

    return {"inserted": len(body.readings)}


@router.get("/{session_id}/readings", response_model=list[ForceReadingResponse])
async def get_readings(
    session_id: UUID,
    user_id: str = Depends(get_user_id),
    sensor_position: str | None = None,
    limit: int = Query(1000, ge=1, le=10000),
    downsample: int = Query(1, ge=1, le=100),
):
    pool = get_pool()

    owner = await pool.fetchval(
        "SELECT user_id FROM sessions WHERE id = $1 AND deleted_at IS NULL", session_id
    )
    if owner is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(owner) != user_id:
        raise HTTPException(status_code=403, detail="Not your session")

    if sensor_position:
        rows = await pool.fetch(
            """
            SELECT * FROM (
                SELECT *, ROW_NUMBER() OVER (ORDER BY time) AS rn
                FROM force_readings
                WHERE session_id = $1 AND sensor_position = $2
            ) sub WHERE sub.rn % $3 = 0
            ORDER BY time ASC LIMIT $4
            """,
            session_id, sensor_position, downsample, limit,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT * FROM (
                SELECT *, ROW_NUMBER() OVER (ORDER BY time) AS rn
                FROM force_readings
                WHERE session_id = $1
            ) sub WHERE sub.rn % $2 = 0
            ORDER BY time ASC LIMIT $3
            """,
            session_id, downsample, limit,
        )

    return [dict(r) for r in rows]
