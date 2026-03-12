import json

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.database import get_pool
from app.models.users import UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/sync", response_model=UserResponse)
async def sync_user(claims: dict = Depends(get_current_user)):
    """Sync Keycloak user to local DB. Called on every login."""
    pool = get_pool()
    user_id = claims["sub"]
    email = claims.get("email", "")
    display = claims.get("name", claims.get("preferred_username", ""))
    first = claims.get("given_name")
    last = claims.get("family_name")

    # Extract role from realm_access
    realm_roles = claims.get("realm_access", {}).get("roles", [])
    role = "climber-free"
    for r in ["admin", "gym-admin", "coach", "climber-elite", "climber-premium"]:
        if r in realm_roles:
            role = r
            break

    row = await pool.fetchrow(
        """
        INSERT INTO users (id, email, display_name, first_name, last_name, role, last_login_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (id) DO UPDATE SET
            email = EXCLUDED.email,
            display_name = EXCLUDED.display_name,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            role = EXCLUDED.role,
            last_login_at = NOW()
        RETURNING *
        """,
        user_id, email, display, first, last, role,
    )
    result = dict(row)
    if isinstance(result.get("climbing_styles"), str):
        result["climbing_styles"] = json.loads(result["climbing_styles"])
    return result
