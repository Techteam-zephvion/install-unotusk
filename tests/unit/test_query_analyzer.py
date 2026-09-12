from apps.api.src.services.context_engine.query_analyzer import analyze_query


def test_query_analyzer_extracts_camelcase_and_snakecase_symbols():
    query = "How does AuthService.login validate the user_session?"
    analyzed = analyze_query(query)

    assert "AuthService" in analyzed.symbol_candidates
    assert "login" in analyzed.symbol_candidates
    assert "user_session" in analyzed.symbol_candidates
    assert "authservice" in analyzed.keywords
    assert "login" in analyzed.keywords


def test_query_analyzer_detects_paths_and_extensions():
    query = "Inspect the routes in apps/api/src/routes/auth.py and service.ts"
    analyzed = analyze_query(query)

    assert "apps/api/src/routes/auth.py" in analyzed.path_candidates
    assert "service.ts" in analyzed.path_candidates


def test_query_analyzer_filters_stopwords_and_expands_concepts():
    query = "Where is the authentication and database connection implemented?"
    analyzed = analyze_query(query)

    # Stopwords like 'where', 'is', 'the', 'and' should be removed from keywords
    assert "where" not in analyzed.keywords
    assert "the" not in analyzed.keywords
    assert "is" not in analyzed.keywords

    # Concept keywords should include domain synonyms
    assert "jwt" in analyzed.concept_keywords
    assert "token" in analyzed.concept_keywords
    assert "postgres" in analyzed.concept_keywords


def test_query_analyzer_handles_empty_or_symbolic_queries():
    analyzed = analyze_query("???")
    assert analyzed.raw_query == "???"
    assert len(analyzed.keywords) == 0
