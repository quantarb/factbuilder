from django.test import TestCase
from facts.graph import build_dependency_graph, detect_cycles
from facts.taxonomy import FactRegistry, FactSpec

class GraphTests(TestCase):
    """
    Tests for dependency graph construction and cycle detection.
    """
    def test_cycle_detection(self) -> None:
        """
        Test that cycles in the dependency graph are detected.
        """
        reg = FactRegistry()
        # A -> B -> C -> A
        reg.register(FactSpec(id="A", kind="computed", data_type="scalar", requires=["B"], dependencies=[], producer=lambda d, c: None, description=""))
        reg.register(FactSpec(id="B", kind="computed", data_type="scalar", requires=["C"], dependencies=[], producer=lambda d, c: None, description=""))
        reg.register(FactSpec(id="C", kind="computed", data_type="scalar", requires=["A"], dependencies=[], producer=lambda d, c: None, description=""))
        
        graph = build_dependency_graph(reg)
        cycles = detect_cycles(graph)
        self.assertTrue(len(cycles) > 0)
        
    def test_no_cycle(self) -> None:
        """
        Test that a graph without cycles is correctly identified.
        """
        reg = FactRegistry()
        # A -> B
        reg.register(FactSpec(id="A", kind="computed", data_type="scalar", requires=["B"], dependencies=[], producer=lambda d, c: None, description=""))
        reg.register(FactSpec(id="B", kind="computed", data_type="scalar", requires=[], dependencies=[], producer=lambda d, c: None, description=""))
        
        graph = build_dependency_graph(reg)
        cycles = detect_cycles(graph)
        self.assertEqual(len(cycles), 0)
