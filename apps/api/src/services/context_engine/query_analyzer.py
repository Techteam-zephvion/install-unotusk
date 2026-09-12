import re
from dataclasses import dataclass, field


@dataclass
class AnalyzedQuery:
    raw_query: str
    keywords: list[str] = field(default_factory=list)
    symbol_candidates: list[str] = field(default_factory=list)
    path_candidates: list[str] = field(default_factory=list)
    concept_keywords: list[str] = field(default_factory=list)


# Stop words that don't help in code retrieval
STOP_WORDS = {
    "a", "an", "the", "in", "on", "of", "for", "to", "from", "with", "by", "at",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "how", "what", "where", "why", "when", "who", "which",
    "can", "could", "should", "would", "will", "this", "that", "these", "those",
    "there", "here", "work", "works", "working", "implemented", "used", "happen", "happens", "involved", "depend", "depends", "connected", "show", "me",
}

# Key architectural domain synonyms
CONCEPT_SYNONYMS: dict[str, list[str]] = {
    "auth": ["auth", "authentication", "login", "signup", "jwt", "token", "password", "session", "user"],
    "database": ["db", "database", "postgres", "sql", "model", "session", "alembic", "migration", "schema"],
    "payment": ["payment", "checkout", "stripe", "billing", "invoice", "charge"],
    "api": ["api", "route", "router", "endpoint", "controller", "request", "response", "handler"],
    "worker": ["worker", "task", "job", "queue", "redis", "background", "dispatch", "process"],
}


def analyze_query(query: str) -> AnalyzedQuery:
    cleaned = query.strip()
    words = re.findall(r"[A-Za-z0-9_.\-/]+", cleaned)

    keywords: list[str] = []
    symbol_candidates: list[str] = []
    path_candidates: list[str] = []
    concept_keywords: list[str] = []

    for word in words:
        # Detect paths (containing '/' or file extensions)
        if "/" in word or re.search(r"\.(ts|tsx|js|jsx|py|go|java|rs|sql|json|md|ya?ml)$", word, re.I):
            path_candidates.append(word.lower())

        # Detect potential symbols:
        # 1. CamelCase (e.g. AuthService, UserService, UserCreate)
        # 2. snake_case with underscores (e.g. process_task, get_current_user)
        # 3. dotted access (e.g. AuthController.login)
        if "." in word:
            parts = word.split(".")
            symbol_candidates.extend(parts)
        elif re.match(r"^[A-Z][a-zA-Z0-9]*[a-z][a-zA-Z0-9]*$", word):
            symbol_candidates.append(word)
        elif "_" in word and re.match(r"^[a-zA-Z0-9_]+$", word):
            symbol_candidates.append(word)

        # Clean word for keywords
        clean_w = word.lower().strip(".,?!:;()[]{}'\"")
        if len(clean_w) > 1 and clean_w not in STOP_WORDS:
            keywords.append(clean_w)
            if "." in clean_w:
                for sub in clean_w.split("."):
                    sub_clean = sub.strip(".,?!:;()[]{}'\"")
                    if len(sub_clean) > 1 and sub_clean not in STOP_WORDS:
                        keywords.append(sub_clean)

            # Check concept expansion
            for _concept, synonyms in CONCEPT_SYNONYMS.items():
                if clean_w in synonyms or any(syn in clean_w for syn in synonyms):
                    concept_keywords.extend(synonyms)

    # Deduplicate while preserving order
    dedup_keywords = list(dict.fromkeys(keywords))
    dedup_symbols = list(dict.fromkeys(symbol_candidates))
    dedup_paths = list(dict.fromkeys(path_candidates))
    dedup_concepts = list(dict.fromkeys(concept_keywords))

    return AnalyzedQuery(
        raw_query=cleaned,
        keywords=dedup_keywords,
        symbol_candidates=dedup_symbols,
        path_candidates=dedup_paths,
        concept_keywords=dedup_concepts,
    )
