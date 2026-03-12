from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_user_id
from app.database import get_pool
from app.schemas import SessionCreate, SessionOut, SessionUpdate

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=201)
async def create_session(
    body: SessionCreate,
    user_id: str = Depends(get_user_id),
):
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO training_sessions
            (user_id, title, session_type, grade, duration_seconds, notes, started_at)
        VALUES ($1, $2, $3, $4, $5, $6, COALESCE($7, now()))
        RETURNING *
        """,
        user_id,
        body.title,
        body.session_type,
        body.grade,
        body.duration_seconds,
        body.notes,
        body.started_at,
    )
    return dict(row)


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    user_id: str = Depends(get_user_id),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT * FROM training_sessions
        WHERE user_id = $1
        ORDER BY started_at DESC
        LIMIT $2 OFFSET $3
        """,
        user_id,
        limit,
        offset,
    )
    return [dict(r) for r in rows]


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: UUID,
    user_id: str = Depends(get_user_id),
):
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM training_sessions WHERE id = $1 AND user_id = $2",
        session_id,
        user_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return dict(row)


@router.patch("/{session_id}", response_model=SessionOut)
async def update_session(
    session_id: UUID,
    body: SessionUpdate,
    user_id: str = Depends(get_user_id),
):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = []
    params: list = []
    for i, (field, value) in enumerate(updates.items(), start=3):
        set_clauses.append(f"{field} = ${i}")
        params.append(value)

    query = f"""
        UPDATE training_sessions
        SET {', '.join(set_clauses)}, updated_at = now()
        WHERE id = $1 AND user_id = $2
        RETURNING *
    """
    pool = get_pool()
    row = await pool.fetchrow(query, session_id, user_id, *params)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return dict(row)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: UUID,
    user_id: str = Depends(get_user_id),
):
    pool = get_pool()
    result = await pool.execute(
        "DELETE FROM training_sessions WHERE id = $1 AND user_id = $2",
        session_id,
        user_id,
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Session not found")
