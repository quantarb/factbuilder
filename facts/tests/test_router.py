from django.test import TestCase
from facts.models import FactDefinition, FactDefinitionVersion, IntentRecognizer
from facts.router import IntentRouter
import re

class RouterTests(TestCase):
    def setUp(self):
        # Create a fact
        self.fact = FactDefinition.objects.create(id="finance.spending", description="Spending")
        self.version = FactDefinitionVersion.objects.create(
            fact_definition=self.fact,
            version=1,
            status='approved',
            code="pass"
        )
        
        # Create recognizer
        self.recognizer = IntentRecognizer.objects.create(
            fact_version=self.version,
            regex_patterns=[r"how much did i spend on (?P<category>\w+)"],
            keywords=["spending", "cost"],
            example_questions=["what is my spending on food?", "how much for groceries?"]
        )
        
        self.router = IntentRouter()

    def test_regex_match(self):
        version, context = self.router.route("how much did i spend on food")
        self.assertEqual(version, self.version)
        self.assertEqual(context['category'], 'food')

    def test_keyword_match(self):
        # Should match based on keywords if regex fails
        version, context = self.router.route("show me spending")
        self.assertEqual(version, self.version)
        
    def test_no_match(self):
        version, context = self.router.route("what is the weather")
        self.assertIsNone(version)
