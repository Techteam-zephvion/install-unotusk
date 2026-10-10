import re
from dataclasses import dataclass, field


@dataclass
class AnalyzedQuery:
    raw_query: str
    keywords: list[str] = field(default_factory=list)
    symbol_candidates: list[str] = field(default_factory=list)
    path_candidates: list[str] = field(default_factory=list)
    concept_keywords: list[str] = field(default_factory=list)
    is_temporal: bool = False
    temporal_intent: str | None = None
    temporal_keywords: list[str] = field(default_factory=list)


# Stop words that don't help in code retrieval
STOP_WORDS = {
    "a",
    "an",
    "the",
    "in",
    "on",
    "of",
    "for",
    "to",
    "from",
    "with",
    "by",
    "at",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "how",
    "what",
    "where",
    "why",
    "when",
    "who",
    "which",
    "can",
    "could",
    "should",
    "would",
    "will",
    "this",
    "that",
    "these",
    "those",
    "there",
    "here",
    "work",
    "works",
    "working",
    "implemented",
    "used",
    "happen",
    "happens",
    "involved",
    "depend",
    "depends",
    "connected",
    "show",
    "me",
}

# Key architectural domain synonyms
CONCEPT_SYNONYMS: dict[str, list[str]] = {
    "auth": [
        "auth",
        "authentication",
        "login",
        "signup",
        "jwt",
        "token",
        "password",
        "session",
        "user",
    ],
    "database": [
        "db",
        "database",
        "postgres",
        "sql",
        "model",
        "session",
        "alembic",
        "migration",
        "schema",
    ],
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
        if "/" in word or re.search(
            r"\.(ts|tsx|js|jsx|py|go|java|rs|sql|json|md|ya?ml)$", word, re.I
        ):
            path_candidates.append(word.lower())

        # Detect potential symbols:
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

    dedup_keywords = list(dict.fromkeys(keywords))
    dedup_symbols = list(dict.fromkeys(symbol_candidates))
    dedup_paths = list(dict.fromkeys(path_candidates))
    dedup_concepts = list(dict.fromkeys(concept_keywords))

    # Detect temporal intent and code evolution queries
    from apps.api.src.services.code_atom.temporal import classify_temporal_intent

    is_temporal, temporal_intent, detected_temporal_keywords = classify_temporal_intent(cleaned)

    return AnalyzedQuery(
        raw_query=cleaned,
        keywords=dedup_keywords,
        symbol_candidates=dedup_symbols,
        path_candidates=dedup_paths,
        concept_keywords=dedup_concepts,
        is_temporal=is_temporal,
        temporal_intent=temporal_intent,
        temporal_keywords=detected_temporal_keywords,
    )


async def analyze_query_async(query: str) -> AnalyzedQuery:
    base = analyze_query(query)
    
    from apps.api.src.config.settings import settings
    provider_name = (settings.LLM_PROVIDER or "offline").strip().lower()
    if provider_name == "offline":
        return base
        
    try:
        from apps.api.src.services.llm.factory import get_llm_provider
        provider = get_llm_provider(provider_name)
        system_prompt = (
            "You are a code intent analyzer. Extract the search intent from the query. "
            "Respond strictly in JSON with fields: 'keywords' (list of semantic terms), "
            "'symbol_candidates' (list of code symbols like AuthController), "
            "'path_candidates' (list of file names/paths), "
            "'concept_keywords' (list of broader architectural concepts like database, auth, api)."
        )
        res = await provider.generate_json(system_prompt, query)
        
        if res:
            base.keywords = list(dict.fromkeys(base.keywords + res.get("keywords", [])))
            base.symbol_candidates = list(dict.fromkeys(base.symbol_candidates + res.get("symbol_candidates", [])))
            base.path_candidates = list(dict.fromkeys(base.path_candidates + res.get("path_candidates", [])))
            base.concept_keywords = list(dict.fromkeys(base.concept_keywords + res.get("concept_keywords", [])))
    except Exception as e:
        import logging
        logging.getLogger("unotusk-query-analyzer").warning(f"LLM query expansion failed: {e}")
        
    return base
