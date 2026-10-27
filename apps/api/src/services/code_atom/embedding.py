import logging
import math
import os
import time
import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import httpx

from apps.api.src.config.settings import settings
from apps.api.src.services.context_engine.retriever import generate_text_embedding

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from apps.api.src.models.chunk import CodeChunk

logger = logging.getLogger(__name__)

DEFAULT_VECTOR_DIM = 1536


class CodeEmbeddingBackend(ABC):
    """Abstract base class for Code-Lane embedding backends."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the embedding provider."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the embedding model."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Expected output vector dimension."""
        ...

    @abstractmethod
    def generate_embedding(
        self,
        text: str,
        input_type: str | None = None,
    ) -> list[float] | None:
        """Generates an embedding vector for text or code."""
        ...

    def embed_text(
        self,
        text: str,
        input_type: str | None = None,
    ) -> list[float] | None:
        """Convenience alias for generate_embedding."""
        return self.generate_embedding(text, input_type=input_type)


class DevelopmentCodeEmbeddingBackend(CodeEmbeddingBackend):
    """
    Deterministic offline synthesizer fallback for zero-hallucination testing
    and environments without external production credentials.
    """

    @property
    def provider_name(self) -> str:
        return "development"

    @property
    def model_name(self) -> str:
        return "deterministic-synthesizer-1536"

    @property
    def dimension(self) -> int:
        return DEFAULT_VECTOR_DIM

    def generate_embedding(
        self,
        text: str,
        input_type: str | None = None,
    ) -> list[float] | None:
        if not text or not text.strip():
            return None
        return generate_text_embedding(text, dim=self.dimension)


class VoyageCodeEmbeddingBackend(CodeEmbeddingBackend):
    """
    Production Code-Lane embedding backend using Voyage AI (defaulting to voyage-code-2).
    Generates 1536-dimensional normalized vectors via Voyage REST API.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "voyage-code-2",
        dimension: int = DEFAULT_VECTOR_DIM,
        timeout: float = 15.0,
        max_retries: int = 2,
        timeout_seconds: float | None = None,
    ):
        if not api_key or not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("VoyageCodeEmbeddingBackend requires a valid, non-empty API key.")
        self.api_key = api_key.strip()
        self._model = model.strip() if model else "voyage-code-2"
        self._dimension = dimension
        self.timeout = float(timeout_seconds if timeout_seconds is not None else timeout)
        self.max_retries = max(0, int(max_retries))

    @property
    def provider_name(self) -> str:
        return "voyage"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def _redact_key(self, text: str) -> str:
        """Sanitizes text by replacing the active API key with [REDACTED]."""
        if not text or not self.api_key:
            return text
        return text.replace(self.api_key, "[REDACTED]")

    def generate_embedding(
        self,
        text: str,
        input_type: str | None = None,
    ) -> list[float] | None:
        if not text or not text.strip():
            return None

        clean_input = text.strip()
        effective_input_type = "query" if input_type == "query" else "document"

        url = "https://api.voyageai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": [clean_input],
            "model": self.model_name,
            "input_type": effective_input_type,
        }

        attempts = 0
        max_attempts = 1 + self.max_retries

        while attempts < max_attempts:
            attempts += 1
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, json=payload, headers=headers)

                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                        except Exception as json_err:
                            logger.warning(
                                "Voyage AI returned invalid JSON payload: %s",
                                self._redact_key(str(json_err)),
                            )
                            return None

                        raw_data = data.get("data", [])
                        if not isinstance(raw_data, list) or not raw_data or "embedding" not in raw_data[0]:
                            logger.warning("Voyage AI response missing embedding data field")
                            return None

                        # Model agreement check (warn on mismatch)
                        returned_model = data.get("model")
                        if returned_model and not (
                            returned_model.startswith(self.model_name)
                            or self.model_name.startswith(returned_model)
                        ):
                            logger.warning(
                                "Voyage AI model discrepancy: requested '%s', received '%s'",
                                self.model_name,
                                returned_model,
                            )

                        vec = raw_data[0]["embedding"]
                        if not isinstance(vec, list) or len(vec) != self.dimension:
                            logger.warning(
                                "Voyage AI dimension mismatch: expected %d, got %s",
                                self.dimension,
                                len(vec) if isinstance(vec, list) else type(vec),
                            )
                            return None

                        # Numeric & finite validation (reject NaN, Inf, non-numeric)
                        clean_vec: list[float] = []
                        for x in vec:
                            try:
                                f_val = float(x)
                                if math.isnan(f_val) or math.isinf(f_val):
                                    logger.warning("Voyage AI returned non-finite embedding element (NaN/Inf)")
                                    return None
                                clean_vec.append(round(f_val, 6))
                            except (TypeError, ValueError):
                                logger.warning("Voyage AI returned non-numeric embedding element: %s", type(x))
                                return None

                        return clean_vec

                    # Handle HTTP Status Errors
                    if resp.status_code in (401, 403):
                        logger.warning(
                            "Voyage AI authentication failure (%d): Invalid or unauthorized credentials.",
                            resp.status_code,
                        )
                        return None  # Permanent auth failure, do not retry

                    if resp.status_code == 429:
                        logger.warning(
                            "Voyage AI rate limit reached (429) on attempt %d/%d.",
                            attempts,
                            max_attempts,
                        )
                        if attempts < max_attempts:
                            time.sleep(0.5 * (2 ** (attempts - 1)))
                            continue
                        return None

                    if resp.status_code >= 500:
                        logger.warning(
                            "Voyage AI server error (%d) on attempt %d/%d: %s",
                            resp.status_code,
                            attempts,
                            max_attempts,
                            self._redact_key(resp.text[:200]),
                        )
                        if attempts < max_attempts:
                            time.sleep(0.5 * (2 ** (attempts - 1)))
                            continue
                        return None

                    logger.warning(
                        "Voyage AI unexpected status code (%d): %s",
                        resp.status_code,
                        self._redact_key(resp.text[:200]),
                    )
                    return None

            except httpx.TimeoutException:
                logger.warning(
                    "Voyage AI request timed out after %.1f seconds on attempt %d/%d.",
                    self.timeout,
                    attempts,
                    max_attempts,
                )
                if attempts < max_attempts:
                    time.sleep(0.5 * (2 ** (attempts - 1)))
                    continue
                return None

            except httpx.RequestError as req_err:
                logger.warning(
                    "Voyage AI network request error on attempt %d/%d: %s",
                    attempts,
                    max_attempts,
                    self._redact_key(str(req_err)),
                )
                if attempts < max_attempts:
                    time.sleep(0.5 * (2 ** (attempts - 1)))
                    continue
                return None

            except Exception as exc:
                logger.warning(
                    "Unexpected error during Voyage AI embedding generation: %s",
                    self._redact_key(str(exc)),
                )
                return None

        return None


def get_code_embedding_backend() -> CodeEmbeddingBackend:
    """
    Resolves the active Code-Lane embedding backend according to configuration.

    - If VOYAGE_API_KEY is configured and provider is set to 'voyage' / 'production',
      activates the Voyage AI production backend.
    - If provider is set to 'voyage' / 'production' but key is missing:
      - In production (APP_ENV == 'production'), raises ValueError (fail-fast policy).
      - In non-production, logs a clear warning and falls back to DevelopmentCodeEmbeddingBackend.
    - If provider is set to 'development', 'offline', or 'test', uses DevelopmentCodeEmbeddingBackend.
    - If an unsupported provider is requested, raises ValueError.
    """
    voyage_key = getattr(settings, "VOYAGE_API_KEY", None) or os.environ.get("VOYAGE_API_KEY")
    raw_provider = getattr(settings, "EMBEDDING_PROVIDER", None) or "development"
    provider = raw_provider.lower().strip()
    app_env = (getattr(settings, "APP_ENV", None) or "development").lower().strip()

    if provider in ("voyage", "production"):
        if voyage_key and voyage_key.strip():
            model_name = getattr(settings, "VOYAGE_MODEL", "voyage-code-2")
            dimension = getattr(settings, "EMBEDDING_DIMENSION", DEFAULT_VECTOR_DIM)
            return VoyageCodeEmbeddingBackend(
                api_key=voyage_key.strip(),
                model=model_name,
                dimension=dimension,
            )

        # Provider requested as voyage/production, but key is missing
        if app_env == "production":
            raise ValueError(
                f"Production embedding provider '{provider}' requested, but VOYAGE_API_KEY is not configured."
            )

        logger.warning(
            "Embedding provider '%s' requested, but VOYAGE_API_KEY is not configured. "
            "Falling back to development deterministic synthesizer.",
            provider,
        )
        return DevelopmentCodeEmbeddingBackend()

    if provider in ("development", "offline", "test"):
        return DevelopmentCodeEmbeddingBackend()

    logger.error("Unsupported embedding provider: '%s'", provider)
    raise ValueError(
        f"Unsupported embedding provider: '{provider}'. "
        f"Supported providers are: 'voyage', 'production', 'development', 'offline', 'test'."
    )


def generate_code_embedding(
    text: str,
    dim: int = DEFAULT_VECTOR_DIM,
    input_type: str | None = None,
    backend: CodeEmbeddingBackend | None = None,
) -> list[float] | None:
    """
    Clean, provider-independent Code-Lane embedding interface:
        generate_code_embedding(text) -> vector

    Guarantees:
    - Decoupled from provider-specific implementation details.
    - Validates returned vector dimension matches dim.
    - Gracefully isolates errors, returning None on failure without corrupting caller data.
    """
    active_backend = backend or get_code_embedding_backend()
    try:
        vec = active_backend.generate_embedding(text, input_type=input_type)
        if vec is None:
            return None
        if not isinstance(vec, list) or len(vec) != dim:
            logger.warning(
                f"Vector dimension mismatch from {active_backend.provider_name}: expected {dim}, got {len(vec) if isinstance(vec, list) else type(vec)}"
            )
            return None
        return vec
    except Exception as exc:
        logger.warning(f"Failed to generate code embedding: {exc}", exc_info=True)
        return None


def format_atom_code_embedding_input(
    commit_message: str | None,
    content: str,
    file_path: str,
    symbol_name: str | None = None,
) -> str:
    """
    Constructs a deterministic, semantic text representation for an atomic code change.

    Preserves the Code-Lane concept:
        commit message + code change/diff
    along with file path and symbol name (when present).

    Does NOT include arbitrary database metadata, primary keys, timestamps, or transient data.
    """
    parts: list[str] = []

    if commit_message and commit_message.strip():
        parts.append(commit_message.strip())

    if file_path and file_path.strip():
        norm_path = file_path.replace("\\", "/").strip().lstrip("/")
        parts.append(f"File: {norm_path}")

    if symbol_name and symbol_name.strip():
        parts.append(f"Symbol: {symbol_name.strip()}")

    if content and content.strip():
        parts.append(content.strip())

    return "\n\n".join(parts)


def generate_atom_code_embedding(
    commit_message: str | None,
    content: str,
    file_path: str,
    symbol_name: str | None = None,
    dim: int = DEFAULT_VECTOR_DIM,
    backend: CodeEmbeddingBackend | None = None,
) -> list[float] | None:
    """
    Generates a validated embedding vector for an atomic code change using the active
    Code-Lane embedding backend.
    """
    embedding_text = format_atom_code_embedding_input(
        commit_message=commit_message,
        content=content,
        file_path=file_path,
        symbol_name=symbol_name,
    )
    if not embedding_text.strip():
        return None

    return generate_code_embedding(
        embedding_text,
        dim=dim,
        input_type="document",
        backend=backend,
    )


def embed_atomic_code_chunk(
    chunk: "CodeChunk",
    symbol_name: str | None = None,
    dim: int = DEFAULT_VECTOR_DIM,
    backend: CodeEmbeddingBackend | None = None,
) -> "CodeChunk":
    """
    Computes and populates the embedding vector for an existing CodeChunk instance
    using its commit, path, content, and provenance metadata.

    Guarantees:
    - Preserves all existing CodeChunk attributes (fingerprint, provenance, IDs, content).
    - If generation fails, chunk.embedding is safely left unchanged without corrupting metadata.
    """
    resolved_symbol_name = symbol_name
    if not resolved_symbol_name and chunk.provenance and isinstance(chunk.provenance, dict):
        resolved_symbol_name = chunk.provenance.get("symbol_name")

    vector = generate_atom_code_embedding(
        commit_message=chunk.commit_message,
        content=chunk.content,
        file_path=chunk.path,
        symbol_name=resolved_symbol_name,
        dim=dim,
        backend=backend,
    )
    if vector is not None:
        chunk.embedding = vector

    return chunk


async def reembed_atom_code_chunks(
    session: "AsyncSession",
    snapshot_id: uuid.UUID | None = None,
    backend: CodeEmbeddingBackend | None = None,
    batch_size: int = 50,
    only_missing: bool = False,
) -> int:
    """
    Safe, deterministic re-embedding path for existing ATOM CodeChunks.

    Guarantees:
    - Replaces only the embedding vector on ATOM-generated CodeChunks.
    - Strictly preserves commit_sha, commit_message, fingerprint, provenance,
      snapshot_id, file_id, symbol_id, path, start_line, end_line, and content.
    - Does NOT reprocess unrelated chunks.
    - Operates in transactional batches.
    - When only_missing=True, filters to chunks where embedding is None.
    """
    from sqlalchemy import or_, select

    from apps.api.src.models.chunk import CodeChunk

    stmt = select(CodeChunk).where(
        or_(
            CodeChunk.commit_sha.isnot(None),
            CodeChunk.fingerprint.isnot(None),
        )
    )
    if snapshot_id is not None:
        stmt = stmt.where(CodeChunk.snapshot_id == snapshot_id)
    if only_missing:
        stmt = stmt.where(CodeChunk.embedding.is_(None))

    res = await session.execute(stmt)
    atom_chunks = res.scalars().all()

    active_backend = backend or get_code_embedding_backend()
    reembedded_count = 0

    for i, chunk in enumerate(atom_chunks):
        resolved_symbol_name = None
        if chunk.provenance and isinstance(chunk.provenance, dict):
            resolved_symbol_name = chunk.provenance.get("symbol_name")

        emb_text = format_atom_code_embedding_input(
            commit_message=chunk.commit_message,
            content=chunk.content,
            file_path=chunk.path,
            symbol_name=resolved_symbol_name,
        )
        if not emb_text.strip():
            continue

        new_vector = generate_code_embedding(
            emb_text,
            dim=DEFAULT_VECTOR_DIM,
            input_type="document",
            backend=active_backend,
        )
        if new_vector is not None:
            chunk.embedding = new_vector
            reembedded_count += 1

        if (i + 1) % batch_size == 0:
            await session.flush()

    await session.flush()
    return reembedded_count
