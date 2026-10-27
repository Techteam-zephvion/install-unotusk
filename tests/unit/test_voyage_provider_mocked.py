"""
Comprehensive offline mocked unit tests for Voyage AI code embedding provider (Phase 2).
All network requests and responses are strictly mocked. No external API calls are made.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.api.src.services.code_atom.embedding import (
    DEFAULT_VECTOR_DIM,
    DevelopmentCodeEmbeddingBackend,
    VoyageCodeEmbeddingBackend,
    get_code_embedding_backend,
)

FAKE_API_KEY = "pa-test-secret-voyage-key-987654321"


# ==============================================================================
# 1. Provider Initialization and Configuration
# ==============================================================================


def test_voyage_provider_initialization_defaults():
    """VoyageCodeEmbeddingBackend initializes with canonical defaults."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY)
    assert backend.provider_name == "voyage"
    assert backend.model_name == "voyage-code-2"
    assert backend.dimension == DEFAULT_VECTOR_DIM
    assert backend.timeout == 15.0
    assert backend.max_retries == 2


def test_voyage_provider_initialization_custom():
    """VoyageCodeEmbeddingBackend respects custom model, dimension, and timeout."""
    backend = VoyageCodeEmbeddingBackend(
        api_key=FAKE_API_KEY,
        model="voyage-code-2",
        dimension=1536,
        timeout=30.0,
        max_retries=1,
    )
    assert backend.model_name == "voyage-code-2"
    assert backend.dimension == 1536
    assert backend.timeout == 30.0
    assert backend.max_retries == 1


def test_voyage_provider_timeout_seconds_alias():
    """VoyageCodeEmbeddingBackend supports timeout_seconds alias for backward compatibility."""
    backend = VoyageCodeEmbeddingBackend(
        api_key=FAKE_API_KEY,
        timeout_seconds=25.0,
    )
    assert backend.timeout == 25.0


def test_voyage_provider_empty_or_whitespace_key_raises_error():
    """VoyageCodeEmbeddingBackend rejects empty or whitespace-only API keys."""
    with pytest.raises(ValueError, match="valid, non-empty API key"):
        VoyageCodeEmbeddingBackend(api_key="")

    with pytest.raises(ValueError, match="valid, non-empty API key"):
        VoyageCodeEmbeddingBackend(api_key="   ")


# ==============================================================================
# 2. Request Serialization, Headers, and Input Types
# ==============================================================================


def test_voyage_request_serialization_document():
    """Verifies endpoint URL, Authorization header, and document input_type."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "object": "list",
        "data": [{"embedding": [0.01] * 1536, "index": 0}],
        "model": "voyage-code-2",
    }

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        vec = backend.generate_embedding("def calculate_total(): pass", input_type="document")
        assert vec is not None
        assert len(vec) == 1536

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.voyageai.com/v1/embeddings"
        assert kwargs["headers"]["Authorization"] == f"Bearer {FAKE_API_KEY}"
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert kwargs["json"]["model"] == "voyage-code-2"
        assert kwargs["json"]["input_type"] == "document"
        assert kwargs["json"]["input"] == ["def calculate_total(): pass"]


def test_voyage_request_serialization_query():
    """Verifies query input_type is serialized when requested."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "object": "list",
        "data": [{"embedding": [0.02] * 1536, "index": 0}],
        "model": "voyage-code-2",
    }

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        vec = backend.generate_embedding("search query for auth", input_type="query")
        assert vec is not None
        kwargs = mock_post.call_args[1]
        assert kwargs["json"]["input_type"] == "query"


def test_voyage_empty_or_whitespace_input_returns_none_without_api_call():
    """Empty or blank text immediately returns None without firing network requests."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY)

    with patch("httpx.Client.post") as mock_post:
        assert backend.generate_embedding("") is None
        assert backend.generate_embedding("   \n\t  ") is None
        mock_post.assert_not_called()


# ==============================================================================
# 3. Response Validation and Numerical Integrity
# ==============================================================================


def test_voyage_successful_numeric_validation():
    """Verifies that valid vector components are properly cast to rounded floats."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY)

    sample_vec = [float(i) / 1000.0 for i in range(1536)]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "object": "list",
        "data": [{"embedding": sample_vec, "index": 0}],
        "model": "voyage-code-2",
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        vec = backend.generate_embedding("sample code")
        assert vec is not None
        assert len(vec) == 1536
        assert all(isinstance(x, float) for x in vec)
        assert vec[0] == 0.0
        assert vec[100] == 0.1


def test_voyage_dimension_mismatch_rejected():
    """Rejects vectors whose length does not match expected dimension (e.g. 1024 vs 1536)."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY, dimension=1536)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "object": "list",
        "data": [{"embedding": [0.01] * 1024, "index": 0}],
        "model": "voyage-code-2",
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        vec = backend.generate_embedding("sample code")
        assert vec is None


def test_voyage_non_finite_values_rejected():
    """Rejects vectors containing NaN, Infinity, or -Infinity values."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY)

    bad_vec_nan = [0.0] * 1535 + [float("nan")]
    bad_resp_nan = MagicMock(status_code=200)
    bad_resp_nan.json.return_value = {"data": [{"embedding": bad_vec_nan}]}

    with patch("httpx.Client.post", return_value=bad_resp_nan):
        assert backend.generate_embedding("test") is None

    bad_vec_inf = [float("inf")] + [0.0] * 1535
    bad_resp_inf = MagicMock(status_code=200)
    bad_resp_inf.json.return_value = {"data": [{"embedding": bad_vec_inf}]}

    with patch("httpx.Client.post", return_value=bad_resp_inf):
        assert backend.generate_embedding("test") is None


def test_voyage_non_numeric_elements_rejected():
    """Rejects vectors containing non-numeric strings or objects."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY)

    corrupt_vec = [0.0] * 1535 + ["not_a_number"]
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"data": [{"embedding": corrupt_vec}]}

    with patch("httpx.Client.post", return_value=mock_resp):
        assert backend.generate_embedding("test") is None


def test_voyage_malformed_json_response():
    """Handles malformed JSON without raising unhandled exceptions."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY)

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.side_effect = ValueError("Invalid JSON format")

    with patch("httpx.Client.post", return_value=mock_resp):
        assert backend.generate_embedding("test") is None


def test_voyage_missing_embedding_or_data_field():
    """Handles responses missing 'data' or 'embedding' keys."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY)

    # Empty data list
    resp1 = MagicMock(status_code=200)
    resp1.json.return_value = {"data": []}
    with patch("httpx.Client.post", return_value=resp1):
        assert backend.generate_embedding("test") is None

    # Missing embedding in item
    resp2 = MagicMock(status_code=200)
    resp2.json.return_value = {"data": [{"index": 0}]}
    with patch("httpx.Client.post", return_value=resp2):
        assert backend.generate_embedding("test") is None


# ==============================================================================
# 4. Error Handling and API Key Redaction
# ==============================================================================


def test_voyage_authentication_error_401_and_403(caplog):
    """Permanent authentication failures (401/403) return None and do not retry."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY, max_retries=2)

    resp_401 = MagicMock(status_code=401, text=f"Unauthorized access with key {FAKE_API_KEY}")

    with patch("httpx.Client.post", return_value=resp_401) as mock_post:
        vec = backend.generate_embedding("code")
        assert vec is None
        # Must not retry on permanent auth error
        mock_post.assert_called_once()

    # Verify API key is redacted and not exposed in log records
    for record in caplog.records:
        assert FAKE_API_KEY not in record.message


def test_voyage_rate_limit_429_with_retry(caplog):
    """429 Rate limit triggers retry up to max_retries."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY, max_retries=2)

    resp_429 = MagicMock(status_code=429, text="Rate limit exceeded")
    resp_200 = MagicMock(status_code=200)
    resp_200.json.return_value = {"data": [{"embedding": [0.05] * 1536}]}

    with patch("time.sleep") as mock_sleep, patch(
        "httpx.Client.post", side_effect=[resp_429, resp_200]
    ) as mock_post:
        vec = backend.generate_embedding("code")
        assert vec is not None
        assert len(vec) == 1536
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once()


def test_voyage_server_error_5xx_with_retry():
    """5xx Server errors trigger retry and return None if all fail."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY, max_retries=1)

    resp_500 = MagicMock(status_code=500, text=f"Internal error for key {FAKE_API_KEY}")

    with patch("time.sleep"), patch("httpx.Client.post", return_value=resp_500) as mock_post:
        vec = backend.generate_embedding("code")
        assert vec is None
        assert mock_post.call_count == 2  # initial + 1 retry


def test_voyage_timeout_handling():
    """Request timeout returns None gracefully without crashing."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY, max_retries=0)

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out")):
        assert backend.generate_embedding("code") is None


def test_voyage_network_error_handling():
    """Network connection error returns None gracefully."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY, max_retries=0)

    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
        assert backend.generate_embedding("code") is None


def test_voyage_api_key_redaction_in_all_error_messages(caplog):
    """Guarantees that sensitive API key is never present in log records during any failure."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY, max_retries=0)

    # Error text embedding the raw key
    leaky_resp = MagicMock(status_code=500, text=f"Crash detail: auth bearer {FAKE_API_KEY} failed")

    with patch("httpx.Client.post", return_value=leaky_resp):
        backend.generate_embedding("sample")

    for record in caplog.records:
        assert FAKE_API_KEY not in record.message


def test_voyage_model_agreement_warning(caplog):
    """Warns if API returns a different model name than configured."""
    backend = VoyageCodeEmbeddingBackend(api_key=FAKE_API_KEY, model="voyage-code-2")

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "object": "list",
        "data": [{"embedding": [0.01] * 1536}],
        "model": "voyage-3-large",
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        vec = backend.generate_embedding("test")
        assert vec is not None

    assert any("model discrepancy" in record.message.lower() for record in caplog.records)


# ==============================================================================
# 5. Fallback Policy and Backend Resolution
# ==============================================================================


def test_get_code_embedding_backend_production_fail_fast():
    """When APP_ENV is production and VOYAGE_API_KEY is missing, fails fast with ValueError."""
    with patch("apps.api.src.config.settings.settings.APP_ENV", "production"), patch(
        "apps.api.src.config.settings.settings.EMBEDDING_PROVIDER", "voyage"
    ), patch("apps.api.src.config.settings.settings.VOYAGE_API_KEY", None), patch.dict(
        "os.environ", {}, clear=True
    ):
        with pytest.raises(ValueError, match="Production embedding provider 'voyage' requested"):
            get_code_embedding_backend()


def test_get_code_embedding_backend_development_fallback_with_warning(caplog):
    """In development, missing VOYAGE_API_KEY falls back cleanly to development backend with warning."""
    with patch("apps.api.src.config.settings.settings.APP_ENV", "development"), patch(
        "apps.api.src.config.settings.settings.EMBEDDING_PROVIDER", "voyage"
    ), patch("apps.api.src.config.settings.settings.VOYAGE_API_KEY", None), patch.dict(
        "os.environ", {}, clear=True
    ):
        backend = get_code_embedding_backend()
        assert isinstance(backend, DevelopmentCodeEmbeddingBackend)
        assert backend.provider_name == "development"
        assert any("falling back to development" in r.message.lower() for r in caplog.records)


def test_get_code_embedding_backend_unsupported_provider():
    """Unsupported provider raises ValueError explicitly."""
    with patch("apps.api.src.config.settings.settings.EMBEDDING_PROVIDER", "unknown_provider"):
        with pytest.raises(ValueError, match="Unsupported embedding provider: 'unknown_provider'"):
            get_code_embedding_backend()


def test_development_backend_explicit_identification():
    """Development backend explicitly identifies itself and never claims to be Voyage."""
    backend = DevelopmentCodeEmbeddingBackend()
    assert backend.provider_name == "development"
    assert backend.model_name == "deterministic-synthesizer-1536"
    assert backend.dimension == 1536

    vec = backend.generate_embedding("def test(): pass")
    assert vec is not None
    assert len(vec) == 1536
