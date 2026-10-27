"""
End-to-End Grounded Feature Specification Evaluation Suite.

Evaluates and verifies all 8 production scenarios:
1. Single function / class mapping
2. Multi-file code evidence preservation
3. Recently changed behavior & commit evolution
4. Renamed, historical, or superseded code handling (zero false current claims)
5. No relevant implementation evidence (zero hallucination)
6. Misleading query with keyword overlap against test mocks / noise
7. Retrieval or generation failure resilience
8. Complete source provenance and audit trail preservation

Measures retrieval quality, specification quality, and execution latency.
"""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.src.schemas.intelligence import (
    EvidenceItem,
)
from apps.api.src.services.context_engine.feature_spec_generator import (
    FeatureSpecificationGenerator,
)
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.intelligence_service import IntelligenceService


def _create_candidate(
    candidate_id: str,
    name: str,
    path: str,
    start_line: int,
    end_line: int,
    content: str,
    entity_type: str = "CHUNK",
    signals: dict[str, float] | None = None,
    metadata: dict | None = None,
) -> RetrievedCandidate:
    return RetrievedCandidate(
        candidate_id=candidate_id,
        entity_type=entity_type,
        name=name,
        path=path,
        start_line=start_line,
        end_line=end_line,
        content=content,
        file_id=uuid.uuid4(),
        symbol_id=uuid.uuid4(),
        signals=signals or {},
        metadata=metadata or {},
    )


# --------------------------------------------------------------------------
# Scenario 1: Exact single function / class mapping
# --------------------------------------------------------------------------
def test_evaluation_scenario_1_single_function_mapping():
    """Scenario 1: Feature request targeting a single existing function."""
    start_time = time.perf_counter()
    project_id = uuid.uuid4()
    req = "Add rate limiting to verify_token authentication"

    evidence = [
        EvidenceItem(
            type="symbol",
            file="src/auth/service.py",
            symbol="verify_token",
            lines="45-80",
            relevance=0.96,
            snippet="def verify_token(token: str) -> bool:\n    return jwt.decode(token, SECRET_KEY)",
            commit_sha="c1a2b3c4d5e6",
            fingerprint="fp-verify-token",
            is_current=True,
            is_superseded=False,
            atomic_code_facts=[{"statement": "Verifies JWT token signature against secret key"}],
        )
    ]

    spec = FeatureSpecificationGenerator.generate_from_evidence(
        project_id=project_id,
        feature_request=req,
        evidence_items=evidence,
        debug_signals={"ranking_model": "multi_signal_v2"},
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert spec.confidence == "HIGH"
    assert spec.cited_files == ["src/auth/service.py"]
    assert spec.cited_symbols == ["verify_token"]
    assert spec.has_superseded_precursors is False
    assert spec.warning is None

    # Happy path scenario must reference verify_token in src/auth/service.py
    happy_path = spec.scenarios[0]
    assert "verify_token" in happy_path.given or "src/auth/service.py" in happy_path.given
    assert "src/auth/service.py" in happy_path.cited_files
    assert "verify_token" in happy_path.cited_symbols

    # Verified facts grounded directly in the evidence
    assert any("Verifies JWT token" in fact for fact in spec.confirmed_code_facts)
    assert elapsed_ms < 100.0  # High performance local synthesis


# --------------------------------------------------------------------------
# Scenario 2: Multi-file code evidence
# --------------------------------------------------------------------------
def test_evaluation_scenario_2_multi_file_structural_evidence():
    """Scenario 2: Feature request spanning multiple files with structural relations."""
    start_time = time.perf_counter()
    project_id = uuid.uuid4()
    req = "Implement transactional webhook dispatch on completed order charge"

    evidence = [
        EvidenceItem(
            type="chunk",
            file="src/services/order.py",
            symbol="OrderService.complete_order",
            lines="110-150",
            relevance=0.94,
            snippet="def complete_order(order_id):\n    payment_svc.charge_card(order.total)",
            commit_sha="sha-order-svc",
            fingerprint="fp-order-complete",
            is_current=True,
            is_superseded=False,
            relationship_path="OrderService -> charge_card [CALLS, hop=1]",
            relationship_type="CALLS",
            relationship_hop=1,
            connected_from="OrderService",
            atomic_code_facts=[{"statement": "Transitions order state to COMPLETED after charging card"}],
        ),
        EvidenceItem(
            type="chunk",
            file="src/services/billing.py",
            symbol="BillingService.charge_card",
            lines="50-95",
            relevance=0.91,
            snippet="def charge_card(amount):\n    return gateway.process(amount)",
            commit_sha="sha-billing-svc",
            fingerprint="fp-charge-card",
            is_current=True,
            is_superseded=False,
            relationship_path="OrderService -> charge_card [CALLS, hop=1]",
            relationship_type="CALLS",
            relationship_hop=1,
            connected_from="OrderService",
            atomic_code_facts=[{"statement": "Executes card charge via payment gateway"}],
        ),
    ]

    spec = FeatureSpecificationGenerator.generate_from_evidence(
        project_id=project_id,
        feature_request=req,
        evidence_items=evidence,
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert spec.confidence == "HIGH"
    assert len(spec.cited_files) == 2
    assert "src/services/billing.py" in spec.cited_files
    assert "src/services/order.py" in spec.cited_files

    # Multi-component integration scenario must be synthesized
    integration_scenario = [s for s in spec.scenarios if "Multi-Component" in s.title or "Integration" in s.title]
    assert len(integration_scenario) == 1
    s2 = integration_scenario[0]
    assert "src/services/billing.py" in s2.given or "src/services/order.py" in s2.given
    assert len(s2.cited_files) == 2

    # Relationship fact preserved
    assert any("OrderService -> charge_card" in fact for fact in spec.confirmed_code_facts)
    assert elapsed_ms < 100.0


# --------------------------------------------------------------------------
# Scenario 3: Recently changed behavior & evolution
# --------------------------------------------------------------------------
def test_evaluation_scenario_3_recent_changed_behavior_evolution():
    """Scenario 3: Feature request grounded in recent commit changes with timestamps."""
    project_id = uuid.uuid4()
    req = "Enhance retry logic introduced in recent commit for payment gateway"

    committed_time = "2026-10-25T16:00:00Z"
    evidence = [
        EvidenceItem(
            type="chunk",
            file="src/services/payment.py",
            symbol="PaymentGateway.process_with_retry",
            lines="30-75",
            relevance=0.95,
            snippet="def process_with_retry(payload, max_retries=3):\n    for attempt in range(max_retries): ...",
            commit_sha="commit_9876543210abcdef",
            commit_message="feat(payment): introduce exponential backoff retry on network timeout",
            committed_at=committed_time,
            fingerprint="fp-retry-logic",
            is_current=True,
            is_superseded=False,
            atomic_code_facts=[{"statement": "Retries payment payload up to 3 times on transient network timeout"}],
        )
    ]

    spec = FeatureSpecificationGenerator.generate_from_evidence(
        project_id=project_id,
        feature_request=req,
        evidence_items=evidence,
    )

    assert spec.confidence == "HIGH"
    assert spec.evidence[0].commit_sha == "commit_9876543210abcdef"
    assert spec.evidence[0].committed_at == committed_time
    assert spec.evidence[0].commit_message == "feat(payment): introduce exponential backoff retry on network timeout"
    assert any("Retries payment payload" in fact for fact in spec.confirmed_code_facts)


# --------------------------------------------------------------------------
# Scenario 4: Renamed, historical, or superseded code
# --------------------------------------------------------------------------
def test_evaluation_scenario_4_superseded_code_never_represented_as_current():
    """Scenario 4: When retrieved code is superseded, never represent it as active current code."""
    project_id = uuid.uuid4()
    req = "Modernize deprecated legacy MD5 password authentication"

    # Only superseded historical code exists
    evidence = [
        EvidenceItem(
            type="chunk",
            file="src/auth/legacy_md5.py",
            symbol="verify_md5_password",
            lines="10-35",
            relevance=0.88,
            snippet="def verify_md5_password(p, h): return md5(p).hexdigest() == h",
            commit_sha="sha_old_md5",
            commit_message="legacy: initial md5 auth",
            is_current=False,
            is_superseded=True,
            superseded_by_sha="sha_new_bcrypt_12345",
            atomic_code_facts=[{"statement": "Computes raw MD5 hash for password checking"}],
        )
    ]

    spec = FeatureSpecificationGenerator.generate_from_evidence(
        project_id=project_id,
        feature_request=req,
        evidence_items=evidence,
    )

    # Must flag superseded precursors
    assert spec.has_superseded_precursors is True
    assert spec.warning is not None
    assert "historical or superseded" in spec.warning.lower()

    # Confidence must not be HIGH when no current code is active
    assert spec.confidence in ("LOW", "MEDIUM")

    # Confirmed facts must NOT claim it is existing active code
    for fact in spec.confirmed_code_facts:
        assert not fact.startswith("Confirmed existing symbol 'verify_md5_password'")
        assert "Historical precursor" in fact or "superseded" in fact.lower()

    # Scenario 1 must state the precursor was superseded or deprecated
    assert "superseded or deprecated" in spec.scenarios[0].given.lower()


# --------------------------------------------------------------------------
# Scenario 5: No relevant implementation evidence (Zero-Hallucination)
# --------------------------------------------------------------------------
def test_evaluation_scenario_5_empty_evidence_zero_hallucination():
    """Scenario 5: Completely unanchored query with zero matching evidence."""
    project_id = uuid.uuid4()
    req = "Deploy autonomous hyperdrive warp stabilizer"

    spec = FeatureSpecificationGenerator.generate_from_evidence(
        project_id=project_id,
        feature_request=req,
        evidence_items=[],
    )

    assert spec.confidence == "LOW"
    assert spec.evidence == []
    assert spec.cited_files == []
    assert spec.cited_symbols == []
    assert spec.confirmed_code_facts == []
    assert spec.warning is not None
    assert "No matching implementation found" in spec.warning

    # Scenario must honestly reflect that no existing implementation exists
    assert "No existing implementation was found" in spec.scenarios[0].given
    assert spec.scenarios[0].cited_files == []
    assert spec.scenarios[0].cited_symbols == []


# --------------------------------------------------------------------------
# Scenario 6: Misleading query with keyword overlap against irrelevant/test code
# --------------------------------------------------------------------------
def test_evaluation_scenario_6_misleading_keyword_overlap_resilience():
    """Scenario 6: Test mocks matching generic keywords are demoted below production logic."""
    query = AnalyzedQuery(
        raw_query="user authentication login flow",
        keywords=["user", "authentication", "login", "flow"],
        symbol_candidates=["login"],
        path_candidates=["auth"],
        concept_keywords=["authenticate", "user"],
        is_temporal=False,
    )

    test_mock_candidate = _create_candidate(
        candidate_id="chunk:tests:mock_auth",
        name="MockUserAuthentication",
        path="tests/mocks/test_auth_mock.py",
        start_line=1,
        end_line=40,
        content="class MockUserAuthentication: def login(self): return True",
        signals={"content_match": 0.9, "symbol_match": 1.0},
    )

    prod_candidate = _create_candidate(
        candidate_id="chunk:prod:auth_service",
        name="login",
        path="apps/api/src/api/routes/auth.py",
        start_line=20,
        end_line=60,
        content="async def login(credentials: UserCredentials): return await auth_service.verify(credentials)",
        signals={"content_match": 0.85, "symbol_match": 1.0, "vector_similarity": 0.92},
        metadata={"commit_sha": "prod_commit_123", "is_current": True},
    )

    ranked = MultiSignalRanker.rank_candidates(
        candidates=[test_mock_candidate, prod_candidate],
        analyzed_query=query,
    )

    # Production code must rank above test mock
    assert ranked[0].candidate.candidate_id == "chunk:prod:auth_service"
    assert any("demoted for non-test query" in r for r in ranked[1].matched_reasons)


# --------------------------------------------------------------------------
# Scenario 7: Retrieval or generation failure resilience
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_evaluation_scenario_7_retrieval_failure_handling():
    """Scenario 7: Database disconnection or engine failure handled gracefully."""
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_session = AsyncMock()
    with (
        patch.object(IntelligenceService, "_verify_project_access", return_value=MagicMock(id=project_id)),
        patch.object(IntelligenceService, "_get_active_snapshot", side_effect=Exception("Database connection timeout")),
    ):
        with pytest.raises(Exception) as exc_info:
            await IntelligenceService.generate_feature_specification(
                session=mock_session,
                user_id=user_id,
                project_id=project_id,
                feature_request="Add login rate limit",
            )
        assert "Database connection timeout" in str(exc_info.value)


# --------------------------------------------------------------------------
# Scenario 8: Specification whose source provenance must be audited
# --------------------------------------------------------------------------
def test_evaluation_scenario_8_source_provenance_audit_preservation():
    """Scenario 8: Complete provenance (fingerprint, commit_sha, lines, facts) audit preservation."""
    project_id = uuid.uuid4()
    req = "Audit security compliance and source provenance for user password hashing"

    evidence = [
        EvidenceItem(
            type="chunk",
            file="src/security/hash.py",
            symbol="hash_password",
            lines="15-42",
            relevance=0.98,
            snippet="def hash_password(pwd: str) -> str:\n    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt(12))",
            commit_sha="d8e7f6a5b4c3210987654321fedcba0987654321",
            commit_message="sec(crypto): enforce bcrypt rounds=12 work factor",
            committed_at="2026-10-22T09:15:00Z",
            repository_id=str(uuid.uuid4()),
            snapshot_id=str(uuid.uuid4()),
            file_id=str(uuid.uuid4()),
            symbol_id=str(uuid.uuid4()),
            fingerprint="fp-bcrypt-salt-12",
            chunk_type="code",
            is_current=True,
            is_superseded=False,
            is_deleted=False,
            relationship_path="UserService -> hash_password [USES, hop=1]",
            relationship_type="USES",
            relationship_hop=1,
            connected_from="UserService",
            retrieval_reason="Direct cryptographic implementation reference",
            provenance={"security_tier": "FIPS-compliant", "audit_passed": True},
            atomic_code_facts=[{"statement": "Enforces bcrypt work factor rounds=12"}],
        )
    ]

    spec = FeatureSpecificationGenerator.generate_from_evidence(
        project_id=project_id,
        feature_request=req,
        evidence_items=evidence,
    )

    assert len(spec.evidence) == 1
    audited = spec.evidence[0]

    # Check 100% provenance retention
    assert audited.commit_sha == "d8e7f6a5b4c3210987654321fedcba0987654321"
    assert audited.commit_message == "sec(crypto): enforce bcrypt rounds=12 work factor"
    assert audited.committed_at == "2026-10-22T09:15:00Z"
    assert audited.fingerprint == "fp-bcrypt-salt-12"
    assert audited.relationship_path == "UserService -> hash_password [USES, hop=1]"
    assert audited.lines == "15-42"
    assert audited.provenance == {"security_tier": "FIPS-compliant", "audit_passed": True}
    assert any("rounds=12" in fact for fact in spec.confirmed_code_facts)
