import uuid
from datetime import timedelta

from apps.api.src.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification():
    raw_password = "SecretPassword123!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password("", hashed) is False


def test_jwt_token_lifecycle():
    user_id = str(uuid.uuid4())
    token = create_access_token(subject=user_id, extra_claims={"email": "test@unotusk.io"})

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["email"] == "test@unotusk.io"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_token_expiration():
    user_id = str(uuid.uuid4())
    # Create expired token (negative delta)
    expired_token = create_access_token(subject=user_id, expires_delta=timedelta(seconds=-10))

    payload = decode_access_token(expired_token)
    assert payload is None


def test_invalid_jwt_token():
    assert decode_access_token("not.a.valid.jwt.token") is None
    assert decode_access_token("") is None


def test_security_vault_token_encryption_and_decryption():
    from apps.api.src.core.security_vault import decrypt_secret, encrypt_secret

    plain_token = "ghp_secureTokenTest1234567890abcdef"
    cipher_token = encrypt_secret(plain_token)

    assert cipher_token != plain_token
    assert not cipher_token.startswith("ghp_")
    decrypted = decrypt_secret(cipher_token)
    assert decrypted == plain_token


def test_security_vault_empty_and_legacy_fallback():
    from apps.api.src.core.security_vault import decrypt_secret, encrypt_secret

    assert encrypt_secret("") == ""
    assert decrypt_secret("") == ""
    # Plain text fallback (legacy compatibility)
    assert decrypt_secret("plain_legacy_token") == "plain_legacy_token"

