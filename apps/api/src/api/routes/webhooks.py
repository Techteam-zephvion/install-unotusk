from __future__ import annotations

import hashlib
import hmac
import logging
import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.database import get_db
from apps.api.src.models.enums import SnapshotStatus
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.workers.dispatcher import TaskDispatcher

logger = logging.getLogger("unotusk-webhooks")

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def verify_github_signature(payload_bytes: bytes, signature_header: str | None) -> bool:
    """Verifies HMAC SHA-256 signature from GitHub webhook header X-Hub-Signature-256."""
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        # If no secret configured in environment, accept payload in development mode
        return True

    if not signature_header:
        return False

    prefix, _, expected_sig = signature_header.partition("=")
    if prefix != "sha256" or not expected_sig:
        return False

    mac = hmac.new(secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), expected_sig)


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def handle_github_webhook(
    request: Request,
    x_github_event: str = Header(default="ping"),
    x_hub_signature_256: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Receives and processes incoming GitHub webhooks:
    - ping: Health / ping verification
    - push: Automated delta/incremental ingestion on commit push
    - pull_request: PR synchronization & structural impact evaluation
    """
    body_bytes = await request.body()
    if not verify_github_signature(body_bytes, x_hub_signature_256):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Hub-Signature-256",
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload",
        ) from None

    event_type = x_github_event.lower()

    if event_type == "ping":
        zen = payload.get("zen", "Keep it logically awesome.")
        return {"status": "pong", "zen": zen}

    if event_type == "push":
        repo_info = payload.get("repository", {})
        full_name = repo_info.get("full_name") or ""
        ref = payload.get("ref", "")
        branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref or "main"
        before_sha = payload.get("before")
        after_sha = payload.get("after")
        commits = payload.get("commits", [])

        if not full_name:
            return {"status": "ignored", "reason": "Missing repository.full_name"}

        # Find registered repository in database
        repo_stmt = select(Repository).where(
            (Repository.full_name == full_name) | (Repository.name == full_name.split("/")[-1])
        )
        repo_res = await db.execute(repo_stmt)
        repository = repo_res.scalar_one_or_none()

        if repository is None:
            logger.info(f"Webhook push received for unregistered repository: {full_name}")
            return {
                "status": "ignored",
                "reason": f"Repository '{full_name}' is not registered in any Unotusk project.",
            }

        # Create a new snapshot record for this incoming push event
        snapshot_id = uuid.uuid4()
        snapshot = RepositorySnapshot(
            id=snapshot_id,
            repository_id=repository.id,
            branch=branch,
            commit_sha=after_sha,
            status=SnapshotStatus.QUEUED,
        )
        db.add(snapshot)
        await db.commit()

        # Enqueue background task
        await TaskDispatcher.dispatch_ingestion_task(
            project_id=str(repository.project_id),
            repository_id=str(repository.id),
            snapshot_id=str(snapshot_id),
            branch=branch,
        )

        logger.info(
            f"Enqueued automated ingestion for {full_name} on branch '{branch}' (commit {after_sha[:8] if after_sha else 'HEAD'})"
        )

        return {
            "status": "enqueued",
            "event": "push",
            "repository": full_name,
            "branch": branch,
            "commit_count": len(commits),
            "snapshot_id": str(snapshot_id),
            "before_sha": before_sha,
            "after_sha": after_sha,
        }

    if event_type == "pull_request":
        action = payload.get("action", "")
        pr_data = payload.get("pull_request", {})
        pr_number = pr_data.get("number")
        base_ref = pr_data.get("base", {}).get("ref", "main")
        head_ref = pr_data.get("head", {}).get("ref", "")
        head_sha = pr_data.get("head", {}).get("sha", "")
        repo_full_name = payload.get("repository", {}).get("full_name", "")

        return {
            "status": "acknowledged",
            "event": "pull_request",
            "action": action,
            "pr_number": pr_number,
            "repository": repo_full_name,
            "base_ref": base_ref,
            "head_ref": head_ref,
            "head_sha": head_sha,
        }

    return {"status": "unhandled_event", "event": event_type}
