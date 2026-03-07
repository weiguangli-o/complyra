"""Password hashing and JWT token creation."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, role: str, user_id: str, default_tenant_id: Optional[str]) -> str:
    now_utc = datetime.now(timezone.utc)
    expire = now_utc + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "uid": user_id,
        "tid": default_tenant_id,
        "exp": expire,
        "iat": now_utc,
    }
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
