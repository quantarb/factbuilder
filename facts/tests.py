from django.test import TestCase
from facts.context import normalize_context, hash_context
from facts.schema_validation import validate_schema_definition, validate_context
from facts.graph import build_dependency_graph, detect_cycles
from facts.executor import execute_expression
from facts.taxonomy import FactRegistry, FactSpec
from facts.models import FactDefinition, FactDefinitionVersion
from datetime import date, datetime
from decimal import Decimal
import networkx as nx

class ContextTests(TestCase):
    def test_normalize_context(self):
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

    def test_hash_context_stability(self):
        ctx1 = {"a": 1, "b": 2}
        ctx2 = {"b": 2, "a": 1}
        self.assertEqual(hash_context(ctx1), hash_context(ctx2))
        
        ctx3 = {"d": date(2023, 1, 1)}
        ctx4 = {"d": "2023-01-01"} # Should match if normalized correctly? 
        # normalize_context converts date to string.
        # But if input is already string, it stays string.
        # So they should match.
        self.assertEqual(hash_context(ctx3), hash_context(ctx4))

class SchemaValidationTests(TestCase):
    def test_validate_schema_definition(self):
        valid_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        }
        validate_schema_definition(valid_schema)
        
        invalid_schema = {"type": "unknown_type"}
        with self.assertRaises(ValueError):
            validate_schema_definition(invalid_schema)

    def test_validate_context(self):
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "minimum": 0}
            },
            "required": ["age"]
        }
        
        validate_context({"age": 25}, schema)
        
        with self.assertRaises(ValueError):
            validate_context({"age": -5}, schema)
            
        with self.assertRaises(ValueError):
            validate_context({}, schema)

class GraphTests(TestCase):
    def test_cycle_detection(self):
        reg = FactRegistry()
        # A -> B -> C -> A
        reg.register(FactSpec(id="A", kind="computed", data_type="scalar", requires=["B"], dependencies=[], producer=lambda d, c: None, description=""))
        reg.register(FactSpec(id="B", kind="computed", data_type="scalar", requires=["C"], dependencies=[], producer=lambda d, c: None, description=""))
        reg.register(FactSpec(id="C", kind="computed", data_type="scalar", requires=["A"], dependencies=[], producer=lambda d, c: None, description=""))
        
        graph = build_dependency_graph(reg)
        cycles = detect_cycles(graph)
        self.assertTrue(len(cycles) > 0)
        
    def test_no_cycle(self):
        reg = FactRegistry()
        # A -> B
        reg.register(FactSpec(id="A", kind="computed", data_type="scalar", requires=["B"], dependencies=[], producer=lambda d, c: None, description=""))
        reg.register(FactSpec(id="B", kind="computed", data_type="scalar", requires=[], dependencies=[], producer=lambda d, c: None, description=""))
        
        graph = build_dependency_graph(reg)
        cycles = detect_cycles(graph)
        self.assertEqual(len(cycles), 0)

class ExecutorTests(TestCase):
    def test_execute_expression(self):
        names = {"a": 10, "b": 20}
        result = execute_expression("a + b", names)
        self.assertEqual(result, 30)
        
    def test_execute_expression_functions(self):
        names = {"items": [1, 2, 3]}
        result = execute_expression("sum(items)", names)
        self.assertEqual(result, 6)
        
    def test_execute_expression_forbidden(self):
        # simpleeval should block access to forbidden things
        names = {}
        with self.assertRaises(Exception):
            execute_expression("__import__('os').system('ls')", names)
