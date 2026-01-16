import networkx as nx
from typing import Dict, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .taxonomy import FactRegistry

def build_dependency_graph(registry: 'FactRegistry') -> nx.DiGraph:
    """
    Builds a directed graph of fact dependencies.
    Nodes are fact IDs.
    Edges are (fact -> dependency).
    """
    graph = nx.DiGraph()
    
    for fact_id, spec in registry.all_specs().items():
        graph.add_node(fact_id)
        # Legacy dependencies
        for dep_id in spec.requires:
            graph.add_edge(fact_id, dep_id)
        # Structured dependencies
        for edge in spec.dependencies:
            graph.add_edge(fact_id, edge.to_fact_id)
            
    return graph

def detect_cycles(graph: nx.DiGraph) -> List[List[str]]:
    """
    Detects cycles in the dependency graph.
    Returns a list of cycles (each cycle is a list of fact IDs).
    """
    try:
        return list(nx.simple_cycles(graph))
    except nx.NetworkXNoCycle:
        return []

def get_topological_sort(graph: nx.DiGraph) -> List[str]:
    """
    Returns a topological sort of the facts.
    Raises NetworkXUnfeasible if the graph contains a cycle.
    """
    try:
        return list(reversed(list(nx.topological_sort(graph))))
    except nx.NetworkXUnfeasible as e:
        raise ValueError(f"Cycle detected in fact dependencies: {e}")
