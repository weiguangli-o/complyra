"""FastAPI dependency injection for authentication and tenant resolution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings
from app.services.users import get_user_profile, user_has_tenant_access


def _extract_token(authorization: Optional[str], cookie_token: Optional[str]) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    if cookie_token:
        return cookie_token
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing access token")


def get_current_user(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    cookie_token: Optional[str] = Cookie(default=None, alias=settings.session_cookie_name),
) -> dict:
    token = _extract_token(authorization, cookie_token)
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    username = payload.get("sub")
    role = payload.get("role")
    user_id = payload.get("uid")
    default_tenant_id = payload.get("tid")
    if not username or not role or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed access token")

    profile = get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")

    return {
        "username": username,
        "role": profile["role"] if profile.get("role") else role,
        "user_id": user_id,
        "default_tenant_id": profile.get("default_tenant_id") or default_tenant_id,
        "tenant_ids": profile["tenant_ids"],
    }


def require_roles(required_roles: list[str]) -> Callable:
    def _role_guard(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in required_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _role_guard


def get_accessible_tenant_ids(user: dict = Depends(get_current_user)) -> list[str]:
    return user["tenant_ids"]


def get_tenant_id(
    user: dict = Depends(get_current_user),
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-ID"),
) -> str:
    tenant_id = x_tenant_id or user.get("default_tenant_id") or settings.default_tenant_id
    if not user_has_tenant_access(user["user_id"], tenant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")
    return tenant_id
