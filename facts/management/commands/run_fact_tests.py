from django.core.management.base import BaseCommand
from facts.models import FactDefinitionVersion
from facts.engine import QAEngine
import json
import sys

# Try to import jsonpath_ng, but don't fail if missing
try:
    from jsonpath_ng import parse as parse_jsonpath
    JSONPATH_AVAILABLE = True
except ImportError:
    JSONPATH_AVAILABLE = False

class Command(BaseCommand):
    help = 'Runs all test cases defined in approved FactDefinitionVersions'

    def handle(self, *args, **options):
        engine = QAEngine()
        versions = FactDefinitionVersion.objects.filter(status='approved')
        
        total = 0
        passed = 0
        failed = 0
        
        self.stdout.write(f"Running tests for {versions.count()} approved fact versions...")
        
        for version in versions:
            if not version.test_cases:
                continue
                
            fact_id = version.fact_definition.id
            self.stdout.write(f"\nTesting {fact_id} v{version.version}...")
            
            for i, test_case in enumerate(version.test_cases):
                total += 1
                context = test_case.get('context', {})
                expected = test_case.get('expected')
                question = test_case.get('question') # Optional question simulation
                
                try:
                    # If question provided, go through full engine
                    if question:
                        result = engine.answer_question(question)
                        # For question tests, we might check if the text contains expected string
                        # or if expected is in the result
                        actual = result
                    else:
                        # Direct resolution test (more robust for logic testing)
                        from facts.taxonomy import resolve_fact, FactStore
                        store = FactStore()
                        instance = resolve_fact(engine.registry, store, fact_id, context)
                        
                        if instance.status == 'error':
                            self.stdout.write(self.style.ERROR(f"  [FAIL] Case {i+1}: Computation Error - {instance.error}"))
                            failed += 1
                            continue

                        actual = instance.value
                    
                    # Assertion
                    if self._check_match(expected, actual):
                        self.stdout.write(self.style.SUCCESS(f"  [PASS] Case {i+1}"))
                        passed += 1
                    else:
                        self.stdout.write(self.style.ERROR(f"  [FAIL] Case {i+1}: Expected {expected}, got {actual}"))
                        failed += 1
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  [FAIL] Case {i+1}: Exception - {str(e)}"))
                    failed += 1

        self.stdout.write("\n--------------------------------------------------")
        self.stdout.write(f"Total: {total}, Passed: {passed}, Failed: {failed}")
        
        if failed > 0:
            sys.exit(1)

    def _check_match(self, expected, actual):
        # 1. Exact match
        if expected == actual:
            return True
            
        # 2. JSONPath match (if expected is a string starting with $)
        if isinstance(expected, str) and expected.startswith('$'):
            if JSONPATH_AVAILABLE:
                try:
                    jsonpath_expr = parse_jsonpath(expected)
                    match = jsonpath_expr.find(actual)
                    return bool(match)
                except Exception:
                    pass
            else:
                # Fallback: Simple dot notation support (e.g. $.key)
                # Very basic implementation
                try:
                    path = expected.lstrip('$').strip('.')
                    parts = path.split('.')
                    current = actual
                    for part in parts:
                        if isinstance(current, dict) and part in current:
                            current = current[part]
                        elif isinstance(current, list) and part.isdigit():
                            current = current[int(part)]
                        else:
                            return False
                    return True
                except Exception:
                    pass
                
        # 3. Subset match for dicts
        if isinstance(expected, dict) and isinstance(actual, dict):
            return all(k in actual and self._check_match(v, actual[k]) for k, v in expected.items())
            
        return False
