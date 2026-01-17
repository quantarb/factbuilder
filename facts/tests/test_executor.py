from django.test import TestCase
from facts.executor import execute_expression

class ExecutorTests(TestCase):
    """
    Tests for the expression executor.
    """
    def test_execute_expression(self) -> None:
        """
        Test simple arithmetic expression execution.
        """
        names = {"a": 10, "b": 20}
        result = execute_expression("a + b", names)
        self.assertEqual(result, 30)
        
    def test_execute_expression_functions(self) -> None:
        """
        Test execution of allowed functions (e.g., sum).
        """
        names = {"items": [1, 2, 3]}
        result = execute_expression("sum(items)", names)
        self.assertEqual(result, 6)
        
    def test_execute_expression_forbidden(self) -> None:
        """
        Test that potentially unsafe operations are blocked.
        """
        # simpleeval should block access to forbidden things
        names = {}
        with self.assertRaises(Exception):
            execute_expression("__import__('os').system('ls')", names)
