from __future__ import annotations

import hashlib
import math
import re

# Semantic Concept Clusters for enhanced neural-like vector embeddings in offline/development mode
CONCEPT_CLUSTERS: dict[str, set[str]] = {
    "auth": {
        "auth", "authenticate", "authentication", "login", "signin", "sign_in",
        "log_in", "credential", "credentials", "password", "jwt", "token",
        "session", "oauth", "bearer", "authorizer", "permission",
    },
    "payment": {
        "payment", "billing", "invoice", "charge", "stripe", "checkout",
        "subscription", "price", "amount", "currency", "gateway", "pay",
    },
    "database": {
        "db", "database", "postgres", "postgresql", "sql", "query",
        "table", "model", "repository", "schema", "entity", "migration", "dao",
    },
    "api": {
        "api", "route", "router", "endpoint", "controller", "handler",
        "request", "response", "rest", "http", "payload", "middleware",
    },
    "worker": {
        "worker", "queue", "redis", "task", "job", "dispatcher",
        "consume", "consumer", "background", "async", "celery",
    },
    "error": {
        "error", "exception", "failure", "fail", "catch", "throw",
        "traceback", "reject", "err", "fatal", "warn",
    },
    "git": {
        "git", "commit", "diff", "branch", "snapshot", "merge",
        "clone", "push", "pull", "pr", "log", "repository",
    },
}

WORD_TO_CONCEPTS: dict[str, list[str]] = {}
for _concept, _words in CONCEPT_CLUSTERS.items():
    for _w in _words:
        WORD_TO_CONCEPTS.setdefault(_w, []).append(_concept)


def compute_cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Computes cosine similarity between two numeric vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def generate_text_embedding(text: str, dim: int = 1536) -> list[float]:
    """
    Generates an enhanced deterministic normalized semantic embedding vector for code or text.
    Combines exact token hashing, subwords, semantic concept projection, and character n-grams.
    """
    if not text or not text.strip():
        return [0.0] * dim

    vec = [0.0] * dim
    tokens = re.findall(r"[A-Za-z0-9_]+|[^\s\w]", text.lower())
    if not tokens:
        return [0.0] * dim

    for token in tokens:
        if len(token) < 2:
            continue
        # 1. Exact token hash
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 1) & 1 else -1.0
        vec[idx] += sign * (1.5 if len(token) > 3 else 1.0)

        # 2. Subwords
        subwords = token.split("_")
        if len(subwords) > 1:
            for sw in subwords:
                if len(sw) >= 2:
                    h_sw = int(hashlib.md5(sw.encode("utf-8")).hexdigest(), 16)
                    idx_sw = h_sw % dim
                    sign_sw = 1.0 if (h_sw >> 1) & 1 else -1.0
                    vec[idx_sw] += sign_sw * 0.8
                    if sw in WORD_TO_CONCEPTS:
                        for c in WORD_TO_CONCEPTS[sw]:
                            h_c = int(hashlib.md5(f"concept_{c}".encode("utf-8")).hexdigest(), 16)
                            vec[h_c % dim] += 2.0

        # 3. Semantic Concept Cluster projection
        if token in WORD_TO_CONCEPTS:
            for c in WORD_TO_CONCEPTS[token]:
                h_c = int(hashlib.md5(f"concept_{c}".encode("utf-8")).hexdigest(), 16)
                vec[h_c % dim] += 2.5

        # 4. Character 3-grams for morphological similarity
        if len(token) >= 4:
            for i in range(len(token) - 2):
                ngram = token[i : i + 3]
                h_ng = int(hashlib.md5(f"ng_{ngram}".encode("utf-8")).hexdigest(), 16)
                vec[h_ng % dim] += 0.3

    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return [0.0] * dim
    return [round(x / norm, 6) for x in vec]
