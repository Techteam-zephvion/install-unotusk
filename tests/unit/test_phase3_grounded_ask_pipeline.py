import asyncio
import importlib.machinery
import sys
import types
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# Pre-load enums module directly to avoid loading all DB models during unit test
enums_mod = importlib.machinery.SourceFileLoader(
    "apps.api.src.models.enums", str(ROOT / "apps/api/src/models/enums.py")
).load_module()
sys.modules["apps.api.src.models.enums"] = enums_mod

# Provide lightweight settings module mock if pydantic is not installed in testing environment
if importlib.util.find_spec("pydantic") is None:
    dummy_settings_mod = types.ModuleType("apps.api.src.config.settings")
    class _MockSettings:
        CONTEXT_BUDGET_TOKENS = 8000
        LLM_PROVIDER = "offline"
        ANTHROPIC_API_KEY = ""
        ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
        GROQ_API_KEY = ""
        DEFAULT_THINKING_BUDGET = 2048
        AUTH_SECRET = "test-secret"
    dummy_settings_mod.settings = _MockSettings()
    sys.modules["apps.api.src.config.settings"] = dummy_settings_mod

from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import (
    RetrievedCandidate,
    _check_definition_match,
)
from apps.api.src.services.llm.claude import ClaudeProvider


class TestPhase3GroundedAskPipeline(unittest.TestCase):
    def test_multilang_definition_match(self):
        """Verify definition pattern recognition across Python, Dart, Java, Rust, Go, C++."""
        # Python
        self.assertTrue(_check_definition_match("def authenticate_user():", "authenticate_user"))
        # Dart
        self.assertTrue(_check_definition_match("class AuthScreen extends StatelessWidget {", "AuthScreen"))
        self.assertTrue(_check_definition_match("Widget build(BuildContext context) {", "build"))
        # Java
        self.assertTrue(_check_definition_match("public class OrderManager {", "OrderManager"))
        self.assertTrue(_check_definition_match("public void processPayment() {", "processPayment"))
        # Rust
        self.assertTrue(_check_definition_match("pub fn handle_connection() -> Result<()> {", "handle_connection"))
        self.assertTrue(_check_definition_match("pub struct NetworkPacket {", "NetworkPacket"))
        # Go
        self.assertTrue(_check_definition_match("func InitializeRouter() *gin.Engine {", "InitializeRouter"))
        # C++
        self.assertTrue(_check_definition_match("virtual void executeQuery() override;", "executeQuery"))

        # Comment or regular text should NOT match definition
        self.assertFalse(_check_definition_match("// TODO: call authenticate_user later", "authenticate_user"))
        self.assertFalse(_check_definition_match("String comment = 'OrderManager is great';", "OrderManager"))

    def test_ast_boost_and_markdown_penalty_ranking(self):
        """Verify 1.8x AST structural boost for code definitions and 0.4x penalty for READMEs."""
        query = analyze_query("How does AuthController handle login?")
        dummy_file_id = uuid.uuid4()

        # Candidate 1: Documentation / README file mentioning login
        cand_readme = RetrievedCandidate(
            candidate_id="chunk:readme",
            entity_type="CHUNK",
            name="README.md",
            path="README.md",
            start_line=1,
            end_line=20,
            content="# AuthController\nThis project handles user login via tokens.",
            file_id=dummy_file_id,
            signals={"content_match": 1.0},
            metadata={"chunk_type": "TEXT"},
        )

        # Candidate 2: Actual AST symbol for AuthController
        cand_symbol = RetrievedCandidate(
            candidate_id="sym:auth",
            entity_type="SYMBOL",
            name="AuthController",
            path="lib/controllers/auth_controller.dart",
            start_line=15,
            end_line=60,
            content="class AuthController {\n  void handleLogin() {}\n}",
            file_id=dummy_file_id,
            signals={"symbol_match": 1.0},
            metadata={"chunk_type": "CLASS"},
        )

        ranked = MultiSignalRanker.rank_candidates([cand_readme, cand_symbol], query)

        self.assertEqual(len(ranked), 2)
        # AuthController symbol candidate MUST outrank README.md by a wide margin
        self.assertEqual(ranked[0].candidate.name, "AuthController")
        self.assertGreater(ranked[0].score, ranked[1].score * 2.0)
        self.assertTrue(any("AST code definition boost" in r for r in ranked[0].matched_reasons))
        self.assertTrue(any("Markdown/README demoted" in r for r in ranked[1].matched_reasons))

    def test_offline_synthesizer_deterministic_grounding(self):
        """Verify that the offline LLM provider synthesizes evidence-grounded answers with citations."""
        provider = ClaudeProvider(api_key="")  # Offline synthesizer
        dummy_file_id = uuid.uuid4()

        cand = RetrievedCandidate(
            candidate_id="sym:payment",
            entity_type="SYMBOL",
            name="PaymentService",
            path="apps/api/src/services/payment.py",
            start_line=12,
            end_line=45,
            content="class PaymentService:\n    def charge(self, amount: float):\n        return True",
            file_id=dummy_file_id,
            signals={"symbol_match": 1.5},
            metadata={"chunk_type": "CLASS"},
        )

        query = analyze_query("Where is PaymentService implemented?")
        ranked = MultiSignalRanker.rank_candidates([cand], query)
        assembled = ContextAssembler.assemble_context(ranked)

        answer = asyncio.run(
            provider.generate_grounded_answer(
                question="Where is PaymentService implemented?",
                project_context=assembled.prompt_context,
                evidence_items=assembled.evidence_items,
                related_entities=assembled.related_entities,
            )
        )

        self.assertIsNotNone(answer.content)
        self.assertGreaterEqual(len(answer.evidence), 1)
        self.assertEqual(answer.evidence[0]["file"], "apps/api/src/services/payment.py")
        self.assertEqual(answer.evidence[0]["lines"], "12-45")
        self.assertIn("PaymentService", answer.content)


if __name__ == "__main__":
    unittest.main()
