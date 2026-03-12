import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_user_id
from app.database import get_pool
from app.models.sessions import (
    SessionCreate,
    SessionEnd,
    SessionListResponse,
    SessionResponse,
    SessionUpdate,
)
from app.models.session_stats import SessionFullResponse, SessionStatsResponse
from app.models.sequences import SequenceResponse
from app.services.sequence_detector import detect_sequences
from app.services.stats_computer import compute_stats

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _parse_session(row: dict) -> dict:
    if isinstance(row.get("tags"), str):
        row["tags"] = json.loads(row["tags"])
    return row


def _parse_stats(row: dict) -> dict:
    if isinstance(row.get("score_breakdown"), str):
        row["score_breakdown"] = json.loads(row["score_breakdown"])
    return row


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(body: SessionCreate, user_id: str = Depends(get_user_id)):
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO sessions
            (client_id, user_id, type, title, description, location_type,
             location_name, climbing_type, grade, started_at, sensor_count,
             force_threshold_kg, sample_rate_hz, tags, notes, recorded_offline)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
        RETURNING *
        """,
        body.client_id, user_id, body.type.value, body.title, body.description,
        body.location_type.value, body.location_name,
        body.climbing_type.value if body.climbing_type else None,
        body.grade, body.started_at, body.sensor_count, body.force_threshold_kg,
        body.sample_rate_hz, json.dumps(body.tags), body.notes, body.recorded_offline,
    )
    return _parse_session(dict(row))


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    user_id: str = Depends(get_user_id),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = None,
    status: str | None = None,
    climbing_type: str | None = None,
):
    pool = get_pool()
    where = ["user_id = $1", "deleted_at IS NULL"]
    params: list = [user_id]
    idx = 2

    for field, value in [("type", type), ("status", status), ("climbing_type", climbing_type)]:
        if value:
            where.append(f"{field} = ${idx}")
            params.append(value)
            idx += 1

    where_sql = " AND ".join(where)

    total = await pool.fetchval(f"SELECT COUNT(*) FROM sessions WHERE {where_sql}", *params)

    offset = (page - 1) * page_size
    params.extend([page_size, offset])
    rows = await pool.fetch(
        f"SELECT * FROM sessions WHERE {where_sql} ORDER BY started_at DESC LIMIT ${idx} OFFSET ${idx+1}",
        *params,
    )

    return SessionListResponse(
        items=[_parse_session(dict(r)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/{session_id}", response_model=SessionFullResponse)
async def get_session(session_id: UUID, user_id: str = Depends(get_user_id)):
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM sessions WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        session_id, user_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    stats_row = await pool.fetchrow(
        "SELECT * FROM session_stats WHERE session_id = $1", session_id
    )
    seq_rows = await pool.fetch(
        "SELECT * FROM sequences WHERE session_id = $1 ORDER BY sensor_position, sequence_number",
        session_id,
    )

    stats = _parse_stats(dict(stats_row)) if stats_row else None

    return SessionFullResponse(
        session=_parse_session(dict(row)),
        stats=stats,
        sequences=[dict(s) for s in seq_rows],
    )


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: UUID, body: SessionUpdate, user_id: str = Depends(get_user_id)
):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = []
    params: list = [session_id, user_id]
    for i, (field, value) in enumerate(updates.items(), start=3):
        if field == "tags":
            value = json.dumps(value)
        set_clauses.append(f"{field} = ${i}")
        params.append(value)

    pool = get_pool()
    row = await pool.fetchrow(
        f"UPDATE sessions SET {', '.join(set_clauses)} "
        f"WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL RETURNING *",
        *params,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _parse_session(dict(row))


@router.post("/{session_id}/end", response_model=SessionFullResponse)
async def end_session(
    session_id: UUID, body: SessionEnd, user_id: str = Depends(get_user_id)
):
    pool = get_pool()
    row = await pool.fetchrow(
        """
        UPDATE sessions SET ended_at = $3, rating = $4, perceived_effort = $5,
            notes = COALESCE($6, notes), status = 'completed'
        WHERE id = $1 AND user_id = $2 AND status = 'active' AND deleted_at IS NULL
        RETURNING *
        """,
        session_id, user_id, body.ended_at, body.rating, body.perceived_effort, body.notes,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Active session not found")

    session = dict(row)

    # Compute sequences and stats
    await detect_sequences(pool, session_id, session["force_threshold_kg"])
    stats = await compute_stats(pool, session_id, user_id)

    seq_rows = await pool.fetch(
        "SELECT * FROM sequences WHERE session_id = $1 ORDER BY sensor_position, sequence_number",
        session_id,
    )

    return SessionFullResponse(
        session=_parse_session(session),
        stats=dict(stats) if stats else None,
        sequences=[dict(s) for s in seq_rows],
    )


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: UUID, user_id: str = Depends(get_user_id)):
    result = await get_pool().execute(
        "UPDATE sessions SET deleted_at = NOW() WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        session_id, user_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Session not found")
