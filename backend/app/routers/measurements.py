import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_user_id
from app.database import get_pool
from app.schemas import MeasurementBatch, MeasurementOut

router = APIRouter(prefix="/api/v1/measurements", tags=["measurements"])


@router.post("", status_code=201)
async def ingest_batch(
    body: MeasurementBatch,
    user_id: str = Depends(get_user_id),
):
    """Batch insert sensor measurements for a training session."""
    pool = get_pool()

    # Verify session belongs to user
    owner = await pool.fetchval(
        "SELECT user_id FROM training_sessions WHERE id = $1",
        body.session_id,
    )
    if owner is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if owner != user_id:
        raise HTTPException(status_code=403, detail="Not your session")

    # Batch insert via executemany for performance
    await pool.executemany(
        """
        INSERT INTO sensor_measurements
            (time, session_id, sensor_type, value, unit, metadata)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        [
            (
                m.time,
                body.session_id,
                m.sensor_type,
                m.value,
                m.unit,
                json.dumps(m.metadata) if m.metadata else None,
            )
            for m in body.measurements
        ],
    )

    return {"inserted": len(body.measurements)}


@router.get("/{session_id}", response_model=list[MeasurementOut])
async def get_measurements(
    session_id: UUID,
    user_id: str = Depends(get_user_id),
    sensor_type: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=10000),
):
    """Retrieve measurements for a session, optionally filtered by sensor type."""
    pool = get_pool()

    # Verify ownership
    owner = await pool.fetchval(
        "SELECT user_id FROM training_sessions WHERE id = $1",
        session_id,
    )
    if owner is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if owner != user_id:
        raise HTTPException(status_code=403, detail="Not your session")

    if sensor_type:
        rows = await pool.fetch(
            """
            SELECT * FROM sensor_measurements
            WHERE session_id = $1 AND sensor_type = $2
            ORDER BY time ASC
            LIMIT $3
            """,
            session_id,
            sensor_type,
            limit,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT * FROM sensor_measurements
            WHERE session_id = $1
            ORDER BY time ASC
            LIMIT $2
            """,
            session_id,
            limit,
        )

    return [dict(r) for r in rows]
