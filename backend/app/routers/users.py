import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_user_id
from app.database import get_pool
from app.models.users import UserProfileUpdate, UserPublicResponse, UserResponse

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _parse_user(row: dict) -> dict:
    if isinstance(row.get("climbing_styles"), str):
        row["climbing_styles"] = json.loads(row["climbing_styles"])
    row["profile_complete"] = (
        row.get("weight_kg") is not None and row.get("climbing_level") is not None
    )
    return row


@router.get("/me", response_model=UserResponse)
async def get_me(user_id: str = Depends(get_user_id)):
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM users WHERE id = $1 AND deleted_at IS NULL", user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="User not found. Call POST /auth/sync first.")
    return _parse_user(dict(row))


@router.patch("/me", response_model=UserResponse)
async def update_me(body: UserProfileUpdate, user_id: str = Depends(get_user_id)):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = []
    params: list = [user_id]
    for i, (field, value) in enumerate(updates.items(), start=2):
        if field == "climbing_styles":
            value = json.dumps(value)
        set_clauses.append(f"{field} = ${i}")
        params.append(value)

    pool = get_pool()
    row = await pool.fetchrow(
        f"UPDATE users SET {', '.join(set_clauses)} WHERE id = $1 AND deleted_at IS NULL RETURNING *",
        *params,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _parse_user(dict(row))


@router.get("/{target_id}/public", response_model=UserPublicResponse)
async def get_public_profile(target_id: UUID, _: str = Depends(get_user_id)):
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT id, display_name, avatar_url, climbing_level, climbing_styles, total_sessions, best_max_force_kg "
        "FROM users WHERE id = $1 AND deleted_at IS NULL",
        target_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _parse_user(dict(row))


@router.delete("/me", status_code=204)
async def delete_me(user_id: str = Depends(get_user_id)):
    pool = get_pool()
    await pool.execute(
        "UPDATE users SET deleted_at = NOW(), email = 'deleted-' || id::text, display_name = 'Deleted User' "
        "WHERE id = $1 AND deleted_at IS NULL",
        user_id,
    )
