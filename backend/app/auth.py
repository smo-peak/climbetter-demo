from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import httpx

from app.config import settings

bearer_scheme = HTTPBearer()

_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


def _invalidate_jwks_cache() -> None:
    global _jwks_cache
    _jwks_cache = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Validate Keycloak JWT and return token claims."""
    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        # Extract key ID from token header
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if key is None:
            # Key rotated — refresh cache and retry once
            _invalidate_jwks_cache()
            jwks = await _get_jwks()
            key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
            if key is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unknown signing key",
                )

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience="account",
            options={"verify_exp": True},
        )
        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


def get_user_id(claims: dict = Depends(get_current_user)) -> str:
    """Extract user ID (sub) from validated JWT claims."""
    return claims["sub"]
