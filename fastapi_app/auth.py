"""
FastAPI authentication — validates Django Token auth.

The client sends the same token it gets from /api/auth/login/:
    Authorization: Token <django-rest-framework-token>

This dependency resolves that token to the Django Student model instance.
"""
from fastapi import Header, HTTPException, status
from asgiref.sync import sync_to_async


async def get_current_student(authorization: str = Header(...)):
    """
    FastAPI dependency: validate a DRF token and return the Student user.

    Raises HTTP 401 if the header is missing, malformed, or the token
    is not found in the database.
    """
    if not authorization.startswith("Token "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header. Expected: Token <token>",
        )

    token_key = authorization.split(" ", 1)[1].strip()
    student = await sync_to_async(_resolve_token)(token_key)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        )
    return student


def _resolve_token(token_key: str):
    """Synchronous DB lookup — wrapped in sync_to_async by the caller."""
    try:
        from rest_framework.authtoken.models import Token
        token = Token.objects.select_related("user").get(key=token_key)
        return token.user
    except Exception:
        return None
