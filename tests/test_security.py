from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password


def test_password_hash_round_trip() -> None:
    password = "StrongPassword!123"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


def test_verify_password_empty_hash_returns_false() -> None:
    assert verify_password("anything", "") is False


def test_access_token_contains_expected_claims() -> None:
    token = create_access_token(
        subject="alice",
        role="admin",
        user_id="user-123",
        default_tenant_id="tenant-001",
    )

    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

    assert payload["sub"] == "alice"
    assert payload["role"] == "admin"
    assert payload["uid"] == "user-123"
    assert payload["tid"] == "tenant-001"
    assert "exp" in payload
    assert "iat" in payload
