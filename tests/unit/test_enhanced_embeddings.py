import unittest

from apps.api.src.services.context_engine.embeddings import (
    compute_cosine_similarity,
    generate_text_embedding,
)


class TestEnhancedEmbeddings(unittest.TestCase):
    def test_semantic_similarity_auth_and_login(self):
        v_auth = generate_text_embedding("authentication")
        v_login = generate_text_embedding("login")
        sim = compute_cosine_similarity(v_auth, v_login)
        # Verify similarity is strongly positive (> 0.50), not 0.0!
        self.assertGreater(sim, 0.50)

    def test_semantic_similarity_payment_and_invoice(self):
        v_stripe = generate_text_embedding("stripe payment gateway")
        v_invoice = generate_text_embedding("billing invoice")
        sim = compute_cosine_similarity(v_stripe, v_invoice)
        self.assertGreater(sim, 0.50)

    def test_orthogonal_domains_low_similarity(self):
        v_auth = generate_text_embedding("authentication login credentials")
        v_stripe = generate_text_embedding("stripe payment billing")
        sim = compute_cosine_similarity(v_auth, v_stripe)
        # Verify orthogonal domains don't produce false matches
        self.assertLess(sim, 0.15)


if __name__ == "__main__":
    unittest.main()
