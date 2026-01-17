from django.test import TestCase
from facts.models import FactDefinition, FactDefinitionVersion, FactInstance
from facts.taxonomy import build_taxonomy, resolve_fact, FactStore
from facts.context import normalize_context

class ProvenanceTests(TestCase):
    """
    Tests for provenance tracking in fact resolution.
    """
    def setUp(self) -> None:
        """
        Set up facts with dependencies for testing provenance.
        """
        # Fact A depends on B
        self.fact_b = FactDefinition.objects.create(id="fact.b", data_type="scalar")
        self.ver_b = FactDefinitionVersion.objects.create(
            fact_definition=self.fact_b,
            version=1,
            status='approved',
            code="def producer(deps, ctx): return 10"
        )
        
        self.fact_a = FactDefinition.objects.create(id="fact.a", data_type="scalar")
        self.ver_a = FactDefinitionVersion.objects.create(
            fact_definition=self.fact_a,
            version=1,
            status='approved',
            requires=["fact.b"],
            code="def producer(deps, ctx): return deps['fact.b'] * 2"
        )
        
        self.registry = build_taxonomy()
        self.store = FactStore()

    def test_provenance_creation(self) -> None:
        """
        Test that provenance information is correctly created and stored.
        """
        instance_a = resolve_fact(self.registry, self.store, "fact.a", {})
        
        self.assertEqual(instance_a.value, 20)
        self.assertIsNotNone(instance_a.provenance)
        
        # Check dependency tracking
        prov = instance_a.provenance
        self.assertIn("dependency_instance_ids", prov)
        self.assertTrue(len(prov["dependency_instance_ids"]) > 0)
        
        # Check timestamp
        self.assertIn("timestamp", prov)
