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
    assert "and" not in analyzed.keywords

    # Sentence-starting stopword 'Where' must not be in symbol_candidates
    assert "Where" not in analyzed.symbol_candidates

    # Concept keywords should include domain synonyms
    assert "jwt" in analyzed.concept_keywords
    assert "token" in analyzed.concept_keywords
    assert "postgres" in analyzed.concept_keywords


def test_query_analyzer_handles_empty_or_symbolic_queries():
    analyzed = analyze_query("???")
    assert analyzed.raw_query == "???"
    assert len(analyzed.keywords) == 0


def test_query_analyzer_preserves_semantic_negation():
    """
    Verifies that semantic negation tokens ('not', 'no', 'never', 'without')
    are preserved and tracked as semantic negation rather than disposable stopwords:
    1. 'Which functions do not call authenticate?' retains 'not' and sets has_negation=True.
    2. 'Find code that is not superseded.' preserves negation alongside temporal intent.
    3. 'Which modules never invoke the legacy handler?' tracks 'never' in negation_keywords.
    4. 'Find functions without external network calls.' tracks 'without' in negation_keywords.
    5. 'There is no authentication check.' tracks 'no'.
    6. Generic conjunctions ('and', 'or', 'but') do NOT trigger negation.
    7. Capitalized negation words ('Not', 'Never', 'No') are not classified as symbol candidates.
    """
    # 1. "not" in query
    q1 = "Which functions do not call authenticate?"
    a1 = analyze_query(q1)
    assert a1.has_negation is True
    assert "not" in a1.negation_keywords
    assert "not" in a1.keywords
    assert "authenticate" in a1.keywords

    # 2. "not superseded" temporal query
    q2 = "Find code that is not superseded."
    a2 = analyze_query(q2)
    assert a2.has_negation is True
    assert "not" in a2.negation_keywords
    assert "not" in a2.keywords
    assert "superseded" in a2.keywords

    # 3. "never" in query
    q3 = "Which modules never invoke the legacy handler?"
    a3 = analyze_query(q3)
    assert a3.has_negation is True
    assert "never" in a3.negation_keywords
    assert "never" in a3.keywords
    assert "handler" in a3.keywords

    # 4. "without" in query
    q4 = "Find functions without external network calls."
    a4 = analyze_query(q4)
    assert a4.has_negation is True
    assert "without" in a4.negation_keywords
    assert "without" in a4.keywords

    # 5. "no" in query
    q5 = "There is no authentication check."
    a5 = analyze_query(q5)
    assert a5.has_negation is True
    assert "no" in a5.negation_keywords
    assert "no" in a5.keywords

    # 6. Generic conjunctions do not trigger negation
    q6 = "Find authentication and database connections or payment routes."
    a6 = analyze_query(q6)
    assert a6.has_negation is False
    assert len(a6.negation_keywords) == 0
    assert "and" not in a6.keywords
    assert "or" not in a6.keywords

    # 7. Sentence-initial negation words are not symbol candidates
    q7 = "Not every function should call AuthController."
    a7 = analyze_query(q7)
    assert "Not" not in a7.symbol_candidates
    assert "AuthController" in a7.symbol_candidates
    assert a7.has_negation is True
    assert "not" in a7.negation_keywords

    q8 = "Never mutate user credentials directly."
    a8 = analyze_query(q8)
    assert "Never" not in a8.symbol_candidates
    assert a8.has_negation is True
    assert "never" in a8.negation_keywords
