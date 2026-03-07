"""User and tenant management service.

Provides authentication, profile lookup, tenant assignment,
and CRUD operations for users and tenants.
"""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

from app.core.security import hash_password, verify_password
from app.db.audit_db import (
    assign_user_tenant,
    create_tenant,
    create_user,
    get_tenant,
    get_user_by_id,
    get_user_by_username,
    list_tenants,
    list_user_tenants,
    list_users,
    user_has_tenant,
)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None

    tenant_ids = [item.tenant_id for item in list_user_tenants(user.user_id)]
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "default_tenant_id": user.default_tenant_id,
        "tenant_ids": tenant_ids,
    }


def get_user_profile(user_id: str) -> Optional[dict]:
    user = get_user_by_id(user_id)
    if not user:
        return None
    tenant_ids = [item.tenant_id for item in list_user_tenants(user.user_id)]
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "default_tenant_id": user.default_tenant_id,
        "tenant_ids": tenant_ids,
    }


def create_tenant_account(tenant_id: str, name: str):
    return create_tenant(tenant_id=tenant_id, name=name)


def list_tenant_accounts():
    return list_tenants()


def get_tenant_account(tenant_id: str):
    return get_tenant(tenant_id)


def create_user_account(username: str, password: str, role: str, default_tenant_id: Optional[str]) -> str:
    user_id = str(uuid4())
    password_hash = hash_password(password)
    create_user(
        user_id=user_id,
        username=username,
        password_hash=password_hash,
        role=role,
        default_tenant_id=default_tenant_id,
    )
    if default_tenant_id:
        assign_user_tenant(user_id=user_id, tenant_id=default_tenant_id)
    return user_id


def list_user_accounts():
    return list_users()


def assign_user_to_tenant(user_id: str, tenant_id: str) -> None:
    assign_user_tenant(user_id=user_id, tenant_id=tenant_id)


def list_user_tenant_access(user_id: str) -> list[str]:
    return [item.tenant_id for item in list_user_tenants(user_id)]


def user_has_tenant_access(user_id: str, tenant_id: str) -> bool:
    if not user_id:
        return False
    return user_has_tenant(user_id=user_id, tenant_id=tenant_id)
