import base64

from cryptography.fernet import Fernet

from apps.api.src.config.settings import settings


def _get_fernet() -> Fernet:
    # Ensure key is 32 URL-safe base64-encoded bytes
    secret = settings.AUTH_SECRET
    # Pad or truncate to 32 bytes
    if len(secret) < 32:
        secret = secret.ljust(32, 'a')
    elif len(secret) > 32:
        secret = secret[:32]
    key = base64.urlsafe_b64encode(secret.encode('utf-8'))
    return Fernet(key)

def encrypt_secret(plain_text: str) -> str:
    if not plain_text:
        return plain_text
    f = _get_fernet()
    return f.encrypt(plain_text.encode('utf-8')).decode('utf-8')

def decrypt_secret(cipher_text: str) -> str:
    if not cipher_text:
        return cipher_text
    f = _get_fernet()
    try:
        return f.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except Exception:
        # Fallback to plain text if not encrypted (legacy)
        return cipher_text
