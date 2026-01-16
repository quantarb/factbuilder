from django.test import TestCase
from django.contrib.auth.models import User
from finance.models import Account, BankTransaction
from facts.engine import QAEngine
from django.core.management import call_command
from datetime import date

class Level0Tests(TestCase):
    def setUp(self):
        # 1. Setup Data (Intents & Facts)
        # We run the command to populate the DB with the Level 0 facts and intents
        call_command('setup_data')
        
        # 2. Setup User & Transactions
        self.user = User.objects.get(username='admin')
        self.acc1 = Account.objects.get(name='Chase Checking')
        self.acc2 = Account.objects.get(name='Chase Credit Card')
        
        # Clear existing txs from setup_data if any, to have clean state for assertions
        BankTransaction.objects.all().delete()
        
        # Add transactions for Acc1
        BankTransaction.objects.create(
            account=self.acc1,
            posting_date=date(2025, 1, 1),
            amount=-100,
            balance=1000.00,
            description="Old Tx"
        )
        BankTransaction.objects.create(
            account=self.acc1,
            posting_date=date(2025, 1, 5),
            amount=-50,
            balance=950.00, # Latest for Acc1
            description="Latest Acc1"
        )
        
        # Add transactions for Acc2
        BankTransaction.objects.create(
            account=self.acc2,
            posting_date=date(2025, 1, 3),
            amount=-20,
            balance=500.00, # Latest for Acc2
            description="Latest Acc2"
        )
        
        # Initialize Engine (which loads intents)
        self.engine = QAEngine()

    def test_cash_balance_question(self):
        """
        Q1: What is my current cash balance?
        Should return sum of 950.00 + 500.00 = 1450.00
        """
        response = self.engine.answer_question("What is my current cash balance?", user=self.user)
        
        # Check text output contains the number (formatted or raw)
        # The fact returns a float, the answer generation might format it.
        # We check for the number in the response text.
        self.assertTrue("1450" in response['text'] or "1,450" in response['text'])
        
    def test_provenance_question(self):
        """
        Q2: Where did this number come from?
        Should return breakdown.
        """
        response = self.engine.answer_question("Where did this number come from?", user=self.user)
        
        text = response['text']
        # Should contain details about accounts and balances
        self.assertIn("Chase Checking", text)
        self.assertTrue("950" in text)
        self.assertIn("Latest Acc1", text)
        
        self.assertIn("Chase Credit Card", text)
        self.assertTrue("500" in text)
        self.assertIn("Latest Acc2", text)
```