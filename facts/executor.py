from simpleeval import SimpleEval, DEFAULT_FUNCTIONS, DEFAULT_NAMES
from typing import Any, Dict, List

# Whitelisted functions for safe expression evaluation
SAFE_FUNCTIONS = {
    'len': len,
    'min': min,
    'max': max,
    'sum': sum,
    'abs': abs,
    'sorted': sorted,
    'round': round,
    'list': list,
    'dict': dict,
    'set': set,
    'tuple': tuple,
    'int': int,
    'float': float,
    'str': str,
    'bool': bool,
}

def execute_expression(expression: str, names: Dict[str, Any]) -> Any:
    """
    Executes a simple expression safely using simpleeval.
    
    Args:
        expression: The expression string to evaluate.
        names: A dictionary of variable names available to the expression.
               This should include dependencies and context parameters.
    """
    evaluator = SimpleEval(
        functions=SAFE_FUNCTIONS,
        names=names
    )
    return evaluator.eval(expression)
