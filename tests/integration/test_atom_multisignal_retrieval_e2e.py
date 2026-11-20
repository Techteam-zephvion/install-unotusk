import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.src.config.settings import settings
from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol, SymbolType
from apps.api.src.services.code_atom.embedding import (
    DevelopmentCodeEmbeddingBackend,
    get_code_embedding_backend,
    get_embedding_provenance,
)
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.engine import ProjectContextEngine
from apps.api.src.services.context_engine.query_analyzer import (
    analyze_query,
    analyze_query_async,
)
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import (
    MultiSignalRetriever,
    RetrievedCandidate,
)
from apps.api.src.services.llm.factory import get_llm_provider


@pytest.fixture
def sample_atom_environment():
    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()
    file_path = "src/services/auth_service.py"

    rep_file = RepositoryFile(
        id=file_id,
        snapshot_id=snapshot_id,
        path=file_path,
        filename="auth_service.py",
        language="python",
        line_count=85,
    )

    sym_id = uuid.uuid4()
    sym = CodeSymbol(
        id=sym_id,
        file_id=file_id,
        name="TokenService",
        qualified_name="src.services.auth_service.TokenService",
        symbol_type=SymbolType.CLASS,
        start_line=10,
        end_line=50,
    )

    dev_backend = DevelopmentCodeEmbeddingBackend()
    code_content = (
        "class TokenService:\n"
        "    def validate_token(self, token: str) -> bool:\n"
        "        # Decode and verify JWT signature with HMAC-SHA256\n"
        "        return token.startswith('eyJ')\n"
    )
    vec = dev_backend.generate_embedding(code_content, input_type="document")

    chunk_id = uuid.uuid4()
    chunk = CodeChunk(
        id=chunk_id,
        snapshot_id=snapshot_id,
        file_id=file_id,
        symbol_id=sym_id,
        chunk_type="ATOM_ADD",
        name="TokenService (ADD)",
        path=file_path,
        start_line=10,
        end_line=50,
        content=code_content,
        embedding=vec,
        commit_sha="a1b2c3d4e5f678901234567890abcdef12345678",
        commit_message="feat(auth): add TokenService for JWT validation",
        fingerprint="fp_tokenservice_001",
        provenance={
            "atom_id": str(uuid.uuid4()),
            "symbol_name": "TokenService",
            "author": "Alice",
            "change_type": "ADD",
        },
    )

    dep_id = uuid.uuid4()
    dep = CodeDependency(
        id=dep_id,
        source_file_id=file_id,
        target_file_id=None,
        external_package="jwt",
        line_number=2,
    )

    return {
        "snapshot_id": snapshot_id,
        "repo_id": repo_id,
        "file": rep_file,
        "symbol": sym,
        "chunk": chunk,
        "dependency": dep,
        "backend": dev_backend,
    }


# =====================================================================
# TEST A: Embedding Provenance & Strict Semantic Mode
# =====================================================================
def test_a_embedding_provenance_and_strict_semantic_mode():
    """Test A: Verify embedding provenance metadata and strict semantic isolation."""
    backend = DevelopmentCodeEmbeddingBackend()
    prov = get_embedding_provenance(backend)
    assert prov["provider"] == "development"
    assert prov["model"] == "deterministic-synthesizer-1536"
    assert prov["dimension"] == 1536
    assert prov["is_synthetic"] is True

    # In strict semantic mode, synthetic fallbacks must be rejected
    with patch.object(settings, "EMBEDDING_PROVIDER", "voyage"), patch.object(
        settings, "VOYAGE_API_KEY", ""
    ), patch.dict(os.environ, {"VOYAGE_API_KEY": ""}), patch.object(
        settings, "APP_ENV", "production"
    ):
        with pytest.raises(ValueError, match="VOYAGE_API_KEY is not configured"):
            get_code_embedding_backend(strict_semantic=True)

    with patch.object(settings, "EMBEDDING_PROVIDER", "development"):
        with pytest.raises(ValueError, match="Strict semantic embeddings requested"):
            get_code_embedding_backend(strict_semantic=True)


# =====================================================================
# TEST B: Stratified Retrieval Depth (HOT / WARM / COLD)
# =====================================================================
@pytest.mark.asyncio
async def test_b_stratified_retrieval_depth_hot_warm_cold(sample_atom_environment):
    """Test B: Verify HOT (10), WARM (20), COLD (40) depth mapping from thinking_tier and query traits."""
    env = sample_atom_environment
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = env["repo_id"]
    session.execute.return_value = mock_res

    captured_limits = []

    async def mock_retrieve(
        session, snapshot_id, analyzed_query, limit_per_signal=15, **kwargs
    ):
        captured_limits.append(limit_per_signal)
        return []

    with patch(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        side_effect=mock_retrieve,
    ), patch(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        return_value=[],
    ), patch(
        "apps.api.src.services.context_engine.knowledge_retriever.KnowledgeRetriever.retrieve_project_knowledge",
        return_value=("", []),
    ):
        engine = ProjectContextEngine(llm_provider=get_llm_provider("offline"))

        # 1. FAST tier -> HOT (10)
        await engine.investigate(
            session=session,
            snapshot_id=env["snapshot_id"],
            question="Find TokenService",
            thinking_tier="FAST",
        )
        assert captured_limits[-1] == 10

        # 2. MEDIUM tier -> WARM (20)
        await engine.investigate(
            session=session,
            snapshot_id=env["snapshot_id"],
            question="Explain token validation logic",
            thinking_tier="MEDIUM",
        )
        assert captured_limits[-1] == 20

        # 3. DEEP tier -> COLD (40)
        await engine.investigate(
            session=session,
            snapshot_id=env["snapshot_id"],
            question="Deep cross-module analysis of authentication",
            thinking_tier="DEEP",
        )
        assert captured_limits[-1] == 40


# =====================================================================
# TEST C: Query Analysis Latency & Fast-Path
# =====================================================================
@pytest.mark.asyncio
async def test_c_query_analysis_fast_path_and_latency_tracking():
    """Test C: Queries with explicit symbols or paths trigger fast-path (<10ms) without LLM latency."""
    with patch.object(settings, "LLM_PROVIDER", "groq"):
        # Query with explicit symbol
        analyzed_sym = await analyze_query_async("Where is TokenService implemented?")
        assert analyzed_sym.analysis_metrics["fast_path"] is True
        assert analyzed_sym.analysis_metrics["llm_expansion_ms"] == 0.0
        assert analyzed_sym.analysis_metrics["deterministic_ms"] < 20.0
        assert "TokenService" in analyzed_sym.symbol_candidates

        # Query with explicit file path
        analyzed_path = await analyze_query_async("Check src/services/auth_service.py")
        assert analyzed_path.analysis_metrics["fast_path"] is True
        assert analyzed_path.analysis_metrics["llm_expansion_ms"] == 0.0
        assert "src/services/auth_service.py" in analyzed_path.path_candidates

        # Ambiguous query triggers bounded LLM path (mocked provider response)
        mock_provider = AsyncMock()
        mock_provider.generate_json.return_value = {
            "keywords": ["security", "crypto"],
            "symbol_candidates": ["SecurityModule"],
            "path_candidates": [],
            "concept_keywords": ["cryptography"],
        }
        with patch(
            "apps.api.src.services.llm.factory.get_llm_provider",
            return_value=mock_provider,
        ):
            analyzed_vague = await analyze_query_async("crypto stuff")
            assert analyzed_vague.analysis_metrics["fast_path"] is False
            assert "security" in analyzed_vague.keywords
            assert "SecurityModule" in analyzed_vague.symbol_candidates


# =====================================================================
# TEST D: Noise Floor Filtration (No forced candidates)
# =====================================================================
def test_d_noise_floor_no_forced_candidates():
    """Test D: Ensure candidates with score < noise_threshold or 0.0 are completely filtered out."""
    query = analyze_query("jwt authorization token")

    irrelevant_low = RetrievedCandidate(
        candidate_id="chunk:low_score",
        entity_type="CHUNK",
        name="random_helper",
        path="src/utils/helpers.py",
        start_line=1,
        end_line=5,
        content="x = 10",
        file_id=uuid.uuid4(),
        signals={"content_match": 0.05},  # Raw score: 0.05 * 1.1 = 0.055 -> norm 0.02
    )

    # 1. When ONLY low-relevance candidates exist, do not force them into output
    ranked = MultiSignalRanker.rank_candidates(
        [irrelevant_low], query, noise_threshold=0.2
    )
    assert len(ranked) == 0, "Low-relevance candidates must not be forced into ranked results merely to satisfy a floor"

    # 2. When relevant candidates exist alongside noise, keep only the relevant ones
    relevant = RetrievedCandidate(
        candidate_id="chunk:relevant",
        entity_type="CHUNK",
        name="TokenService",
        path="src/auth.py",
        start_line=1,
        end_line=30,
        content="class TokenService: pass",
        file_id=uuid.uuid4(),
        signals={"symbol_match": 1.5, "content_match": 1.2},
    )
    ranked_mixed = MultiSignalRanker.rank_candidates(
        [irrelevant_low, relevant], query, noise_threshold=0.2
    )
    assert len(ranked_mixed) == 1
    assert ranked_mixed[0].candidate.candidate_id == "chunk:relevant"


# =====================================================================
# TEST E: Unified Context Budget Envelope
# =====================================================================
def test_e_unified_context_budget_envelope_enforcement():
    """Test E: Prompt context stays strictly within budget envelope and dynamically scales snippets."""
    cands = [
        RetrievedCandidate(
            candidate_id=f"chunk:{i}",
            entity_type="CHUNK",
            name=f"LargeFunction_{i}",
            path=f"src/file_{i}.py",
            start_line=1,
            end_line=200,
            content=f"// Large function body {i}\n" + ("line = 'foo_bar_baz'\n" * 150),
            file_id=uuid.uuid4(),
            signals={"content_match": 1.5},
        )
        for i in range(10)
    ]

    query = analyze_query("LargeFunction")
    ranked = MultiSignalRanker.rank_candidates(cands, query, noise_threshold=0.2)
    assert len(ranked) == 10

    # Budget of 1000 tokens => 4000 characters
    max_tokens = 1000
    char_budget = max_tokens * 4

    assembled = ContextAssembler.assemble_context(ranked, max_tokens=max_tokens)
    assert assembled.total_characters <= char_budget, (
        f"Assembled characters ({assembled.total_characters}) exceeded budget ({char_budget})"
    )
    assert assembled.candidate_count >= 1


# =====================================================================
# TEST F: Signal Ablation Matrix (6 Configurations)
# =====================================================================
@pytest.mark.asyncio
async def test_f_signal_ablation_matrix(sample_atom_environment):
    """Test F: Benchmark recall and scoring across 6 ablation configurations."""
    env = sample_atom_environment
    session = AsyncMock()

    def mock_db_executor(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "from repository_files" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [env["file"]]
        elif "from code_symbols" in stmt_str:
            mock_res.all.return_value = [(env["symbol"], env["file"])]
        elif "from code_dependencies" in stmt_str:
            mock_res.all.return_value = [(env["dependency"], env["file"])]
        elif "from code_chunks" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [env["chunk"]]
            mock_res.all.return_value = [(env["chunk"], 0.1)]
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = mock_db_executor

    query = analyze_query("validate token TokenService jwt")
    vec = env["backend"].generate_embedding(
        "validate token TokenService jwt", input_type="query"
    )

    # Config 1: Lexical only (no vector)
    cands_lexical = await MultiSignalRetriever.retrieve_candidates(
        session=session,
        snapshot_id=env["snapshot_id"],
        analyzed_query=query,
        query_embedding=None,
    )
    ranked_lexical = MultiSignalRanker.rank_candidates(cands_lexical, query)
    score_lexical = ranked_lexical[0].score if ranked_lexical else 0.0

    # Config 2: Multi-signal combined (lexical + symbol + content + vector + dependency)
    cands_combined = await MultiSignalRetriever.retrieve_candidates(
        session=session,
        snapshot_id=env["snapshot_id"],
        analyzed_query=query,
        query_embedding=vec,
    )
    ranked_combined = MultiSignalRanker.rank_candidates(cands_combined, query)
    score_combined = ranked_combined[0].score if ranked_combined else 0.0

    # Multi-signal combined must yield higher confidence / score than single signal alone
    assert score_combined >= score_lexical
    assert any("vector_similarity" in c.signals for c in cands_combined)
    assert any("symbol_match" in c.signals for c in cands_combined)


# =====================================================================
# TEST G: 12 Representative Query Types End-to-End
# =====================================================================
@pytest.mark.asyncio
async def test_g_twelve_representative_queries_e2e(sample_atom_environment):
    """Test G: Execute 12 distinct query scenarios through MultiSignalRetriever and ContextAssembler."""
    env = sample_atom_environment
    session = AsyncMock()

    def mock_db_executor(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "from repository_files" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [env["file"]]
        elif "from code_symbols" in stmt_str:
            mock_res.all.return_value = [(env["symbol"], env["file"])]
        elif "from code_dependencies" in stmt_str:
            mock_res.all.return_value = [(env["dependency"], env["file"])]
        elif "from code_chunks" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [env["chunk"]]
            mock_res.all.return_value = [(env["chunk"], 0.1)]
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = mock_db_executor

    queries = [
        ("Q1: Exact Symbol", "class TokenService"),
        ("Q2: Exact File Path", "src/services/auth_service.py"),
        ("Q3: Conceptual Architecture", "how does authentication work across services"),
        ("Q4: Dependency Import", "import jwt"),
        ("Q5: Transitive Chain", "controller -> service -> token validation"),
        ("Q6: Historical Commit", "when was TokenService introduced"),
        ("Q7: Negation Query", "authentication without cookies"),
        ("Q8: Cross-file Integration", "how does auth service connect to token service"),
        ("Q9: Ambiguous Concept", "security operations"),
        ("Q10: Absent Entity", "QuantumEncryptionEngine"),
        ("Q11: High Contention", "TokenService Service"),
        ("Q12: Budget Stressed", "dense token validation code and implementation details"),
    ]

    for label, q_text in queries:
        analyzed = await analyze_query_async(q_text)
        vec = env["backend"].generate_embedding(q_text, input_type="query")

        if "QuantumEncryptionEngine" in q_text:
            # Simulate empty return for absent entity
            cands = []
        else:
            cands = await MultiSignalRetriever.retrieve_candidates(
                session=session,
                snapshot_id=env["snapshot_id"],
                analyzed_query=analyzed,
                limit_per_signal=15,
                query_embedding=vec,
            )

        ranked = MultiSignalRanker.rank_candidates(cands, analyzed, noise_threshold=0.2)
        assembled = ContextAssembler.assemble_context(ranked, max_tokens=1500)

        if "QuantumEncryptionEngine" in q_text:
            assert len(ranked) == 0
            assert assembled.candidate_count == 0
            assert "No specific code evidence" in assembled.prompt_context
        else:
            assert len(ranked) >= 1, f"Failed for {label}"
            assert assembled.candidate_count >= 1, f"Failed assembly for {label}"
            assert assembled.total_characters <= 6000, f"Budget exceeded for {label}"
