import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_creates_non_plaintext_hash():
    password_hash = hash_password("SecurePass123!")

    assert password_hash != "SecurePass123!"
    assert verify_password("SecurePass123!", password_hash) is True
    assert verify_password("WrongPass123!", password_hash) is False


def test_access_token_round_trip_returns_user_id():
    token = create_access_token(user_id=42)

    assert decode_access_token(token) == 42


@pytest.mark.parametrize(
    "token",
    [
        "",
        "not-a-valid-token",
    ],
)
def test_decode_access_token_rejects_invalid_tokens(token: str):
    with pytest.raises(ValueError, match="Invalid or expired access token"):
        decode_access_token(token)
