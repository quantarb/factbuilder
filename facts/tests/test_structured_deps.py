from django.test import TestCase
from facts.models import FactDefinition, FactDefinitionVersion
from facts.taxonomy import build_taxonomy, resolve_fact, FactStore

class StructuredDependencyTests(TestCase):
    """
    Tests for structured dependencies with parameter mapping.
    """
    def setUp(self) -> None:
        """
        Set up facts with structured dependencies and parameter mapping.
        """
        # Fact B takes a parameter 'x'
        self.fact_b = FactDefinition.objects.create(id="fact.b", data_type="scalar")
        self.ver_b = FactDefinitionVersion.objects.create(
            fact_definition=self.fact_b,
            version=1,
            status='approved',
            code="def producer(deps, ctx): return ctx.get('x', 0)"
        )
        
        # Fact A depends on B, mapping context 'val' -> 'x'
        self.fact_a = FactDefinition.objects.create(id="fact.a", data_type="scalar")
        self.ver_a = FactDefinitionVersion.objects.create(
            fact_definition=self.fact_a,
            version=1,
            status='approved',
            dependencies=[{
                "id": "fact.b",
                "with": {"x": "{{val}}"}
            }],
            code="def producer(deps, ctx): return deps['fact.b']"
        )
        
        self.registry = build_taxonomy()
        self.store = FactStore()

    def test_param_mapping(self) -> None:
        """
        Test that parameters are correctly mapped from parent context to dependency context.
        """
        # Call A with val=5. Should call B with x=5.
        instance_a = resolve_fact(self.registry, self.store, "fact.a", {"val": 5})
        
        self.assertEqual(instance_a.value, 5)
        
        # Verify B was called with x=5
        # We can check the store for B's instance
        # But we need to know the hash.
        # Instead, let's check dependencies of A
        dep_instance = instance_a.dependencies.first().dependency_instance
        self.assertEqual(dep_instance.context['x'], 5)
