import pytest

from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_is_not_plaintext_and_verifies() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", hashed)


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip() -> None:
    token = create_access_token(user_id=42)
    assert decode_token(token, TokenType.ACCESS) == 42


def test_refresh_token_roundtrip() -> None:
    token = create_refresh_token(user_id=42)
    assert decode_token(token, TokenType.REFRESH) == 42


def test_access_token_rejected_as_refresh_token() -> None:
    token = create_access_token(user_id=42)
    with pytest.raises(InvalidTokenError):
        decode_token(token, TokenType.REFRESH)


def test_garbage_token_is_invalid() -> None:
    with pytest.raises(InvalidTokenError):
        decode_token("not-a-real-token", TokenType.ACCESS)
