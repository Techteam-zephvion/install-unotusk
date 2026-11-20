import hashlib
import hmac
import json
import time
import uuid
from typing import Any

import jwt

from apps.api.src.config.settings import settings

UNOTUSK_PROJECT_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def derive_canonical_project_id(org_slug: str, project_slug: str) -> uuid.UUID:
    """Deterministically derives the exact same Project UUID across both planes."""
    key = f"{org_slug.strip().lower()}:{project_slug.strip().lower()}"
    return uuid.uuid5(UNOTUSK_PROJECT_NAMESPACE, key)


def derive_data_plane_secret(master_secret: str, project_slug: str) -> str:
    """Cryptographically derive a project-scoped shared secret from the cluster master authority key."""
    key_bytes = master_secret.strip().encode("utf-8")
    msg = f"unotusk-data-plane:{project_slug.strip().lower()}".encode()
    return hmac.new(key_bytes, msg, hashlib.sha256).hexdigest()


def mint_federation_token(
    *,
    user_id: uuid.UUID,
    email: str,
    name: str,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    project_slug: str,
    role: str,
    ttl_seconds: int = 60,
    target_secret: str | None = None,
) -> str:
    now = int(time.time())
    payload = {
        "iss": "unotusk-control-plane",
        "aud": f"unotusk-data-plane:{project_id}",
        "sub": str(user_id),
        "email": email,
        "name": name,
        "org_id": str(org_id),
        "project_id": str(project_id),
        "project_slug": project_slug,
        "role": role,
        "iat": now,
        "exp": now + ttl_seconds,
        "token_use": "data_plane_federation",
    }
    # Secret priority: explicit target secret > effective federation secret
    secret = target_secret or settings.effective_federation_secret
    return jwt.encode(
        payload,
        secret,
        algorithm="HS256",
    )


def verify_federation_token(
    token: str,
    expected_project_id: uuid.UUID | str,
) -> dict[str, Any] | None:
    # Accept token verified by effective_federation_secret, or derived secret from cluster authority
    candidate_secrets = [settings.effective_federation_secret]
    derived = derive_data_plane_secret(settings.effective_federation_secret, str(expected_project_id))
    if derived not in candidate_secrets:
        candidate_secrets.append(derived)

    for secret in candidate_secrets:
        try:
            # First decode token verifying signature and issuer
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
                issuer="unotusk-control-plane",
            )
            if payload.get("token_use") != "data_plane_federation":
                continue

            # Verify target audience / project ref binding
            ref_str = str(expected_project_id).strip().lower()
            aud = str(payload.get("aud") or "").lower()
            proj_id = str(payload.get("project_id") or "").lower()
            proj_slug = str(payload.get("project_slug") or "").lower()

            if (
                ref_str != proj_id
                and ref_str != proj_slug
                and aud != f"unotusk-data-plane:{ref_str}"
                and aud != ref_str
            ):
                continue

            return payload
        except Exception:
            continue

    return None


def sign_cluster_sync_payload(
    payload_dict: dict[str, Any],
    timestamp: int | None = None,
) -> tuple[str, str, bytes]:
    ts = str(timestamp if timestamp is not None else int(time.time()))
    raw_body = json.dumps(
        payload_dict, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    msg = ts.encode("utf-8") + b"." + raw_body
    secret_bytes = settings.effective_federation_secret.encode("utf-8")
    sig = hmac.new(secret_bytes, msg, hashlib.sha256).hexdigest()
    return ts, sig, raw_body


def verify_cluster_sync_signature(
    ts_header: str | None,
    sig_header: str | None,
    raw_body: bytes,
    max_skew_sec: int = 300,
) -> bool:
    if not ts_header or not sig_header:
        return False
    try:
        ts = int(ts_header)
    except ValueError:
        return False
    if abs(int(time.time()) - ts) > max_skew_sec:
        return False
    msg = ts_header.encode("utf-8") + b"." + raw_body
    candidate_keys = [settings.effective_federation_secret.encode("utf-8")]
    if settings.AUTH_SECRET and settings.AUTH_SECRET.encode("utf-8") not in candidate_keys:
        candidate_keys.append(settings.AUTH_SECRET.encode("utf-8"))

    for key in candidate_keys:
        expected = hmac.new(key, msg, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, sig_header):
            return True
    return False
