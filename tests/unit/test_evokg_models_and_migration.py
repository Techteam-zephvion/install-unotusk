import importlib
import uuid

from sqlalchemy import inspect as sa_inspect

migration_0011 = importlib.import_module("apps.api.alembic.versions.0011_evokg_triplets")
from apps.api.src.models.evokg import EvoKGTriplet


def test_1_evokg_triplet_model_metadata():
    """Verify EvoKGTriplet table name, primary key, and columns."""
    assert EvoKGTriplet.__tablename__ == "evokg_triplets"

    mapper = sa_inspect(EvoKGTriplet)
    columns = {c.key: c for c in mapper.columns}

    # Identity
    assert "id" in columns
    assert columns["id"].primary_key is True
    assert "repository_id" in columns
    assert columns["repository_id"].nullable is False
    assert "snapshot_id" in columns
    assert columns["snapshot_id"].nullable is True
    assert "branch" in columns
    assert columns["branch"].nullable is False
    assert "subject_id" in columns
    assert columns["subject_id"].nullable is False
    assert "relation" in columns
    assert columns["relation"].nullable is False
    assert "object_id" in columns
    assert columns["object_id"].nullable is False

    # Optional AST FKs
    assert "file_id" in columns
    assert columns["file_id"].nullable is True
    assert "symbol_id" in columns
    assert columns["symbol_id"].nullable is True

    # Classification & Exclusivity
    assert "is_exclusive" in columns
    assert columns["is_exclusive"].nullable is False
    assert "scope_key" in columns
    assert columns["scope_key"].nullable is False

    # Temporal Metadata
    assert "valid_from" in columns
    assert columns["valid_from"].nullable is True
    assert "valid_to" in columns
    assert columns["valid_to"].nullable is True
    assert "observation_time" in columns
    assert columns["observation_time"].nullable is True
    assert "commit_sha" in columns
    assert columns["commit_sha"].nullable is True
    assert "superseded_by_id" in columns
    assert columns["superseded_by_id"].nullable is True
    assert "supersedes_id" in columns
    assert columns["supersedes_id"].nullable is True

    # Confidence & Uncertainty
    assert "confidence_score" in columns
    assert columns["confidence_score"].nullable is False
    assert "confidence_level" in columns
    assert columns["confidence_level"].nullable is False
    assert "is_uncertain" in columns
    assert columns["is_uncertain"].nullable is False
    assert "has_temporal_conflict" in columns
    assert columns["has_temporal_conflict"].nullable is False
    assert "conflict_detail" in columns
    assert columns["conflict_detail"].nullable is True

    # Provenance
    assert "fingerprint" in columns
    assert columns["fingerprint"].nullable is False
    assert "provenance" in columns
    assert columns["provenance"].nullable is False


def test_2_evokg_indexes_defined():
    """Verify required indexes are defined on EvoKGTriplet."""
    table = EvoKGTriplet.__table__
    index_names = {idx.name for idx in table.indexes}

    expected_indexes = {
        "ix_evokg_active_outgoing",
        "ix_evokg_active_incoming",
        "ix_evokg_temporal_lookup",
        "ix_evokg_exclusive_conflict",
        "ix_evokg_snapshot",
        "ix_evokg_commit",
        "ix_evokg_repo_fingerprint",
        "uq_evokg_active_exclusive",
    }
    for exp in expected_indexes:
        assert exp in index_names, f"Expected index {exp} not found on evokg_triplets table"


def test_3_migration_structure_and_revision_chain():
    """Verify Alembic migration 0011 follows correct revision chain and exports callables."""
    assert migration_0011.revision == "0011_evokg_triplets"
    assert migration_0011.down_revision == "0010_code_chunk_atom_metadata"
    assert callable(migration_0011.upgrade)
    assert callable(migration_0011.downgrade)


def test_4_triplet_instantiation_defaults():
    """Verify EvoKGTriplet model instantiates with proper conservative defaults and nullable fields."""
    repo_id = uuid.uuid4()
    triplet = EvoKGTriplet(
        repository_id=repo_id,
        branch="main",
        subject_id="pkg/auth.py::verify_token",
        relation="DEFINES_RETURN_TYPE",
        object_id="bool",
        fingerprint="fp_test_123",
    )
    assert triplet.repository_id == repo_id
    assert triplet.branch == "main"
    assert triplet.is_exclusive is False
    assert triplet.scope_key == "default"
    assert triplet.valid_from is None
    assert triplet.valid_to is None
    # Conservative defaults: missing evidence never defaults to HIGH
    assert triplet.is_uncertain is True
    assert triplet.has_temporal_conflict is False
    assert triplet.confidence_score == 0.50
    assert triplet.confidence_level == "UNCERTAIN"


def test_5_confidence_calibration_and_uncertainty_consistency():
    """Verify confidence category and uncertainty flags remain consistent under various inputs."""
    repo_id = uuid.uuid4()

    # High confidence evidence
    t_high = EvoKGTriplet(
        repository_id=repo_id,
        subject_id="a",
        relation="DEFINES",
        object_id="b",
        fingerprint="fp_1",
        confidence_level="HIGH",
        confidence_score=0.95,
    )
    assert t_high.confidence_level == "HIGH"
    assert t_high.is_uncertain is False
    assert t_high.confidence_score == 0.95

    # Uncertain flag overrides HIGH confidence category
    t_conflict = EvoKGTriplet(
        repository_id=repo_id,
        subject_id="a",
        relation="DEFINES",
        object_id="b",
        fingerprint="fp_2",
        confidence_level="HIGH",
        confidence_score=0.95,
        is_uncertain=True,
    )
    assert t_conflict.confidence_level == "UNCERTAIN"
    assert t_conflict.is_uncertain is True
    assert t_conflict.confidence_score <= 0.50

    # Unknown confidence category maps to UNCERTAIN
    t_unknown = EvoKGTriplet(
        repository_id=repo_id,
        subject_id="a",
        relation="DEFINES",
        object_id="b",
        fingerprint="fp_3",
        confidence_level="SOME_UNRECOGNIZED_LEVEL",
    )
    assert t_unknown.confidence_level == "UNCERTAIN"
    assert t_unknown.is_uncertain is True

