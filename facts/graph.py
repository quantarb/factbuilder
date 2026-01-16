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
        for dep_id in spec.requires:
            graph.add_edge(fact_id, dep_id)
            
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
    # Reverse the graph because topological_sort expects edges (u, v) where u comes before v.
    # Our graph has edges (fact -> dependency), meaning dependency must be computed before fact.
    # So we want dependency to come first in the sort.
    # If A depends on B, we have A -> B.
    # Topological sort of A -> B gives [A, B].
    # But we want [B, A] (compute B first).
    # So we can just reverse the result of topological sort on the original graph?
    # Or reverse the graph edges?
    # If A -> B (A depends on B), then B must be computed before A.
    # Standard topological sort gives an ordering where for every edge u->v, u comes before v.
    # So if A->B, A comes before B. This is the opposite of execution order.
    # So we want the reverse of topological sort.
    
    try:
        return list(reversed(list(nx.topological_sort(graph))))
    except nx.NetworkXUnfeasible as e:
        raise ValueError(f"Cycle detected in fact dependencies: {e}")
