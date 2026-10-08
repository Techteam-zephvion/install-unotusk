import logging
import os
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
    Production Code-Lane embedding backend using Voyage AI (voyage-code-2).
    Generates 1536-dimensional normalized vectors via Voyage REST API.
    """

    def __init__(self, api_key: str, model: str = "voyage-code-2"):
        self.api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "voyage"

    @property
    def model_name(self) -> str:
        return self._model

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

        url = "https://api.voyageai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": [text],
            "model": self.model_name,
            "input_type": input_type or "document",
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                if resp.status_code != 200:
                    logger.warning(
                        f"Voyage AI API returned status {resp.status_code}: {resp.text}"
                    )
                    return None

                data = resp.json()
                raw_data = data.get("data", [])
                if not raw_data or "embedding" not in raw_data[0]:
                    logger.warning("Voyage AI response missing embedding data")
                    return None

                vec = raw_data[0]["embedding"]
                if not isinstance(vec, list) or len(vec) != self.dimension:
                    logger.warning(
                        f"Voyage AI dimension mismatch: expected {self.dimension}, got {len(vec) if isinstance(vec, list) else type(vec)}"
                    )
                    return None

                return [round(float(x), 6) for x in vec]
        except Exception as exc:
            logger.warning(f"Voyage AI embedding request error: {exc}", exc_info=True)
            return None


def get_code_embedding_backend() -> CodeEmbeddingBackend:
    """
    Resolves the active Code-Lane embedding backend according to configuration.

    - If VOYAGE_API_KEY is configured and provider is set to 'voyage' / 'production',
      activates the Voyage AI production backend.
    - Otherwise, falls back cleanly to the development deterministic synthesizer backend.
    """
    voyage_key = getattr(settings, "VOYAGE_API_KEY", None) or os.environ.get("VOYAGE_API_KEY")
    provider = (getattr(settings, "EMBEDDING_PROVIDER", None) or "development").lower().strip()

    if (provider in ("voyage", "production")) and voyage_key and voyage_key.strip():
        model_name = getattr(settings, "VOYAGE_MODEL", "voyage-code-2")
        return VoyageCodeEmbeddingBackend(api_key=voyage_key.strip(), model=model_name)

    if provider in ("voyage", "production") and (not voyage_key or not voyage_key.strip()):
        logger.warning(
            "Production embedding provider '%s' requested, but VOYAGE_API_KEY is not configured. "
            "Falling back to development deterministic synthesizer.",
            provider,
        )

    return DevelopmentCodeEmbeddingBackend()


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
) -> int:
    """
    Safe, deterministic re-embedding path for existing ATOM CodeChunks.

    Guarantees:
    - Replaces only the embedding vector on ATOM-generated CodeChunks.
    - Strictly preserves commit_sha, commit_message, fingerprint, provenance,
      snapshot_id, file_id, symbol_id, path, start_line, end_line, and content.
    - Does NOT reprocess unrelated chunks.
    - Operates in transactional batches.
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
