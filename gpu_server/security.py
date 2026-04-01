from fastapi import Header, HTTPException, status

from gpu_server.config import settings


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.api_key}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header",
        )
