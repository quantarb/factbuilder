from django.test import TestCase
from django.contrib.auth.models import User
from facts.models import FactDefinition, FactDefinitionVersion, FactInstance
from facts.taxonomy import normalize_context, hash_context, safe_execute, create_dynamic_producer
from datetime import date, datetime
import json

class ContextNormalizationTests(TestCase):
    def test_normalize_context(self):
        ctx = {
            'user': 'should_be_removed',
            'b': 2,
            'a': 1,
            'date': date(2023, 1, 1),
            'nested': {'x': 10, 'user': 'remove_me'}
        }
        normalized = normalize_context(ctx)
        self.assertNotIn('user', normalized)
        self.assertNotIn('user', normalized['nested'])
        self.assertEqual(normalized['date'], '2023-01-01')
        self.assertEqual(list(normalized.keys()), ['b', 'a', 'date', 'nested']) # Keys not sorted yet, just dict

    def test_hash_context_stability(self):
        ctx1 = {'a': 1, 'b': 2}
        ctx2 = {'b': 2, 'a': 1}
        self.assertEqual(hash_context(ctx1), hash_context(ctx2))
        
        ctx3 = {'nested': {'x': 1, 'y': 2}}
        ctx4 = {'nested': {'y': 2, 'x': 1}}
        self.assertEqual(hash_context(ctx3), hash_context(ctx4))

class SafeExecutionTests(TestCase):
    def test_safe_execution_success(self):
        code = "return 1 + 1"
        producer = create_dynamic_producer(code)
        result = safe_execute(producer, {}, {})
        self.assertEqual(result, 2)

    def test_safe_execution_timeout(self):
        code = "while True: pass"
        producer = create_dynamic_producer(code)
        with self.assertRaises(TimeoutError):
            safe_execute(producer, {}, {}, timeout=1)

    def test_safe_execution_import_blocked(self):
        code = "import os; return os.getcwd()"
        producer = create_dynamic_producer(code)
        with self.assertRaises(RuntimeError):
            safe_execute(producer, {}, {})

class FactModelTests(TestCase):
    def test_data_type_enum(self):
        defn = FactDefinition.objects.create(id='test_fact', data_type=FactDefinition.FactValueType.SCALAR)
        self.assertEqual(defn.data_type, 'scalar')
        
    def test_concurrency_uniqueness(self):
        defn = FactDefinition.objects.create(id='test_fact')
        ver = FactDefinitionVersion.objects.create(fact_definition=defn, version=1, code="pass")
        ctx = {'a': 1}
        ctx_hash = hash_context(ctx)
        
        FactInstance.objects.create(fact_version=ver, context_hash=ctx_hash, status='success')
        
        with self.assertRaises(Exception): # IntegrityError
            FactInstance.objects.create(fact_version=ver, context_hash=ctx_hash, status='error')
