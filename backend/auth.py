import os

from fastapi import HTTPException, Request, status

GENERIC_AUTH_ERROR = "Invalid or missing API key."


def _auth_enabled() -> bool:
    return os.getenv("AUTH_ENABLED", "false").strip().lower() in ("1", "true", "yes")


def _valid_keys() -> set[str]:
    raw = os.getenv("API_KEYS", "")
    return {key.strip() for key in raw.split(",") if key.strip()}


def verify_api_key(request: Request) -> None:
    """FastAPI dependency enforcing X-API-Key when AUTH_ENABLED is true.

    Defaults to a no-op so existing usage keeps working until a deployer
    opts in.
    """
    if not _auth_enabled():
        return

    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key not in _valid_keys():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_AUTH_ERROR)


def rate_limit_key(request: Request) -> str:
    """Key used to bucket rate limiting.

    Uses the caller's API key when auth is enabled and one was supplied, so
    each key gets its own budget. Falls back to client IP otherwise, which
    is also the behavior when auth is disabled entirely.
    """
    api_key = request.headers.get("X-API-Key")
    if _auth_enabled() and api_key:
        return f"key:{api_key}"

    client = request.client
    return f"ip:{client.host if client else 'unknown'}"
