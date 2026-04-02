"""API Key authentication and user identity management."""

import structlog
from fastapi import HTTPException, Header, Depends
from typing import Optional, Dict
from core.config import settings

log = structlog.get_logger()

# Valid API keys mapped to user identifiers
VALID_API_KEYS: Dict[str, str] = {
    settings.api_key_dev: "dev-user",
    settings.api_key_test: "test-user",
}


async def verify_api_key(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify API key from Authorization header.

    Expected format: "Bearer {api_key}"
    Returns: user_id (string identifier)
    Raises: HTTPException if invalid
    """
    if not settings.api_key_enabled:
        return "anonymous"

    if not authorization:
        log.warning("auth_missing")
        raise HTTPException(
            status_code=403,
            detail="Missing Authorization header. Use: Authorization: Bearer {api_key}"
        )

    # Parse "Bearer {api_key}"
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        log.warning("auth_invalid_format", header=authorization[:20])
        raise HTTPException(
            status_code=403,
            detail="Invalid Authorization format. Use: Bearer {api_key}"
        )

    api_key = parts[1]

    if api_key not in VALID_API_KEYS:
        log.warning("auth_invalid_key", key_prefix=api_key[:10])
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    user_id = VALID_API_KEYS[api_key]
    log.info("auth_success", user_id=user_id)
    return user_id


# Dependency for endpoints that require auth
async def get_current_user(user_id: str = Depends(verify_api_key)) -> str:
    """Dependency injection for authenticated user_id."""
    return user_id
