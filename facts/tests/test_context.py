from django.test import TestCase
from facts.context import normalize_context, hash_context
from datetime import date
from decimal import Decimal

class ContextTests(TestCase):
    """
    Tests for context normalization and hashing.
    """
    def test_normalize_context(self) -> None:
        """
        Test that context is correctly normalized (keys sorted, types converted, excluded keys removed).
        """
        ctx = {
            "b": 2,
            "a": 1,
            "date": date(2023, 1, 1),
            "nested": {"y": 20, "x": 10},
            "user": "should_be_removed",
            "decimal": Decimal("10.5")
        }
        normalized = normalize_context(ctx)
        
        self.assertEqual(normalized['a'], 1)
        self.assertEqual(normalized['b'], 2)
        self.assertEqual(normalized['date'], "2023-01-01")
        self.assertEqual(normalized['nested'], {"x": 10, "y": 20}) # Dicts are not sorted by normalize, but hash handles it
        self.assertNotIn('user', normalized)
        self.assertEqual(normalized['decimal'], 10.5)

    def test_hash_context_stability(self) -> None:
        """
        Test that context hashing is stable regardless of key order and equivalent types.
        """
        ctx1 = {"a": 1, "b": 2}
        ctx2 = {"b": 2, "a": 1}
        self.assertEqual(hash_context(ctx1), hash_context(ctx2))
        
        ctx3 = {"d": date(2023, 1, 1)}
        ctx4 = {"d": "2023-01-01"} # Should match if normalized correctly? 
        # normalize_context converts date to string.
        # But if input is already string, it stays string.
        # So they should match.
        self.assertEqual(hash_context(ctx3), hash_context(ctx4))
