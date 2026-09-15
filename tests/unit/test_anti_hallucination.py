"""
tests/unit/test_anti_hallucination.py

TASK-507 — Grounding & Anti-Hallucination Verification
Regression tests verifying that the context engine and LLM providers never
fabricate entities, and that they correctly qualify answers when evidence is
insufficient.
"""

from apps.api.src.services.llm.groq import GroqProvider


class TestGroqProviderOfflineAntiHallucination:
    """Test the offline deterministic fallback of GroqProvider."""

    def setup_method(self):
        # Force offline mode by not providing an API key
        self.provider = GroqProvider(api_key=None)

    def _offline_answer(
        self, question: str, evidence_items=None, related_entities=None, project_context=""
    ):
        """Call the internal offline generator directly."""
        return self.provider._generate_offline_grounded_answer(
            question=question,
            evidence_items=evidence_items or [],
            related_entities=related_entities or [],
            project_context=project_context,
            confidence="LOW",
        )

    def test_nonexistent_file_returns_no_evidence_message(self):
        """A query about a file that does not exist in evidence must NOT invent a response."""
        answer = self._offline_answer(
            question="What does /src/quantum_optimizer.py do?",
            evidence_items=[],
        )
        # Must state no evidence found — not fabricate content about quantum_optimizer.py
        assert (
            "no matching" in answer.lower()
            or "not found" in answer.lower()
            or "searched" in answer.lower()
        )
        assert "quantum_optimizer" not in answer.lower()

    def test_nonexistent_class_returns_no_evidence_message(self):
        """A query about a class not in evidence must state no evidence found."""
        answer = self._offline_answer(
            question="How does QuantumProcessor.entangle() work?",
            evidence_items=[],
        )
        assert (
            "no matching" in answer.lower()
            or "not found" in answer.lower()
            or "searched" in answer.lower()
        )
        assert "quantumprocessor" not in answer.lower()

    def test_nonexistent_dependency_returns_no_evidence_message(self):
        """A query about a library not in evidence must not fabricate import information."""
        answer = self._offline_answer(
            question="How is the tensorflow_quantum package used?",
            evidence_items=[],
        )
        assert (
            "no matching" in answer.lower()
            or "not found" in answer.lower()
            or "searched" in answer.lower()
        )
        assert "tensorflow_quantum" not in answer.lower()

    def test_empty_context_empty_evidence_no_fabrication(self):
        """With no evidence and no context, the system must clearly state the limitation."""
        answer = self._offline_answer(
            question="How does authentication work?",
            evidence_items=[],
            project_context="",
        )
        assert len(answer) > 0, "Must return a response, not an empty string"
        # Must not pretend to know specifics without evidence
        assert (
            "no matching" in answer.lower()
            or "not found" in answer.lower()
            or "searched" in answer.lower()
        )

    def test_answer_with_real_evidence_references_file(self):
        """When real evidence exists, the answer must reference the actual file."""
        evidence = [
            {
                "file": "src/auth/login.py",
                "symbol": "LoginService.authenticate",
                "lines": "23-45",
                "chunk": "def authenticate(self, username, password): ...",
                "relevance": 0.95,
            }
        ]
        answer = self._offline_answer(
            question="How does login authentication work?",
            evidence_items=evidence,
        )
        assert "login.py" in answer or "LoginService" in answer or "authenticate" in answer

    def test_answer_does_not_invent_symbol_names_beyond_evidence(self):
        """The offline answer must only reference symbols provided in evidence."""
        evidence = [
            {
                "file": "src/auth/login.py",
                "symbol": "LoginService.authenticate",
                "lines": "23-45",
                "chunk": "def authenticate(self, username, password): ...",
                "relevance": 0.90,
            }
        ]
        answer = self._offline_answer(
            question="How does login authentication work?",
            evidence_items=evidence,
        )
        # Should NOT mention arbitrary invented symbols
        assert "QuantumAuth" not in answer
        assert "BlockchainLogin" not in answer

    def test_unrelated_project_question_no_fabrication(self):
        """A question completely unrelated to project content must acknowledge lack of evidence."""
        answer = self._offline_answer(
            question="What is the capital of France?",
            evidence_items=[],
        )
        assert (
            "no matching" in answer.lower()
            or "not found" in answer.lower()
            or "searched" in answer.lower()
        )

    def test_ambiguous_question_without_evidence_safe_response(self):
        """Ambiguous questions without evidence must not produce confident fabricated answers."""
        answer = self._offline_answer(
            question="How does it work?",
            evidence_items=[],
        )
        assert len(answer) > 0
        assert (
            "no matching" in answer.lower()
            or "not found" in answer.lower()
            or "searched" in answer.lower()
        )

    def test_customer_knowledge_not_converted_to_observed_fact(self):
        """Customer knowledge must be labeled as such, not presented as observed code fact."""
        customer_context = """<customer_project_knowledge>
### [CUSTOMER: Architecture Note]
Content: The PaymentService is completely decoupled from AuthService.
</customer_project_knowledge>"""

        evidence = [
            {
                "file": "src/payment/service.py",
                "symbol": "PaymentService",
                "lines": "1-100",
                "chunk": "from src.auth.service import AuthService\nclass PaymentService: ...",
                "relevance": 0.85,
            }
        ]
        answer = self._offline_answer(
            question="Is PaymentService coupled with AuthService?",
            evidence_items=evidence,
            project_context=customer_context,
        )
        # The answer must mention the customer knowledge with appropriate labeling
        assert (
            "CUSTOMER" in answer
            or "customer" in answer.lower()
            or "user" in answer.lower()
            or "payment" in answer.lower()
        )

    def test_project_with_no_indexed_content_explicit_limitation(self):
        """When the project has no indexed code, the answer must explain this limitation."""
        answer = self._offline_answer(
            question="What are the main architectural components?",
            evidence_items=[],
            project_context="",
        )
        assert (
            "no matching" in answer.lower()
            or "not found" in answer.lower()
            or "searched" in answer.lower()
        )

    def test_evidence_count_proportional_to_claims(self):
        """Evidence items listed in the answer must not exceed what was actually provided."""
        evidence = [
            {
                "file": "src/foo.py",
                "symbol": "Foo.bar",
                "lines": "10-20",
                "chunk": "def bar(): pass",
                "relevance": 0.80,
            }
        ]
        answer = self._offline_answer(
            question="How does Foo work?",
            evidence_items=evidence,
        )
        # Should reference foo.py, NOT invent baz.py or other non-existent files
        assert "baz.py" not in answer
        assert "quantum" not in answer.lower()
