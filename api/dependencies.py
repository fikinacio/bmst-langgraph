"""
FastAPI dependency injection — API key authentication.
"""
from fastapi import Header, HTTPException, status

from core.settings import settings


async def verify_api_key(x_api_key: str = Header(...)) -> None:
    """
    Validate the X-Api-Key header sent by the caller.

    If BMST_API_KEY is not set in settings (empty string), the check is skipped
    so that local development works without configuration.  In production the key
    must be set and must match exactly.

    Raises:
        HTTPException(401): When the key is set and the provided value does not match.
    """
    if not settings.BMST_API_KEY:
        # Dev mode — key not configured, allow all requests
        return
    if x_api_key != settings.BMST_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
