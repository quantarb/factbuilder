from django.test import TestCase
from django.contrib.auth.models import User
from finance.models import Account, BankTransaction
from facts.engine import QAEngine
from facts.models import FactDefinition, FactDefinitionVersion, IntentRecognizer, FactInstance
from decimal import Decimal
from datetime import date, timedelta

class Level0TrustGroundTruthTest(TestCase):
    def setUp(self):
        # 1. Create User
        self.user = User.objects.create_user(username='testuser', password='password')
        
        # 2. Create Accounts
        self.acc1 = Account.objects.create(name='Checking', user=self.user)
        self.acc2 = Account.objects.create(name='Savings', user=self.user)
        
        # 3. Create Transactions
        # Account 1: Latest balance is 1000.00
        BankTransaction.objects.create(
            account=self.acc1,
            details='DEBIT',
            posting_date=date(2023, 1, 1),
            description='Old Tx',
            amount=-50.00,
            type='DEBIT',
            balance=500.00
        )
        BankTransaction.objects.create(
            account=self.acc1,
            details='DEBIT',
            posting_date=date(2023, 1, 5),
            description='Latest Tx Acc1',
            amount=-10.00,
            type='DEBIT',
            balance=1000.00
        )
        # Add a newer transaction with NULL balance (should be ignored)
        BankTransaction.objects.create(
            account=self.acc1,
            details='PENDING',
            posting_date=date(2023, 1, 6),
            description='Pending Tx',
            amount=-20.00,
            type='DEBIT',
            balance=None
        )

        # Account 2: Latest balance is 2500.50
        BankTransaction.objects.create(
            account=self.acc2,
            details='CREDIT',
            posting_date=date(2023, 1, 4),
            description='Latest Tx Acc2',
            amount=2500.50,
            type='CREDIT',
            balance=2500.50
        )

        # 4. Seed Facts (Simulate setup_data)
        self.setup_level0_facts()
        
        self.engine = QAEngine()

    def setup_level0_facts(self):
        # 1. money.cash_balance
        cash_balance_code = """
user = context.get('user')
if not user:
    return {'error': 'No user context'}

accounts = Account.objects.filter(user=user)
total = Decimal('0.00')

for acc in accounts:
    # Get latest transaction with non-null balance
    tx = BankTransaction.objects.filter(account=acc, balance__isnull=False).order_by('-posting_date', '-id').first()
    if tx:
        # balance is float in DB, convert to string first for Decimal safety
        total += Decimal(str(tx.balance))

return {
    "cash_balance": float(total),
    "currency": "USD"
}
"""
        self._create_fact_with_intent(
            id="money.cash_balance",
            desc="Current total cash balance across all accounts",
            code=cash_balance_code,
            data_type="dict",
            regex_patterns=[r"what is my (current )?cash balance\??"],
            keywords=["cash", "balance"]
        )

        # 2. money.cash_balance_breakdown
        breakdown_code = """
user = context.get('user')
if not user:
    return {'error': 'No user context'}

accounts = Account.objects.filter(user=user)
breakdown = []
total = Decimal('0.00')

for acc in accounts:
    tx = BankTransaction.objects.filter(account=acc, balance__isnull=False).order_by('-posting_date', '-id').first()
    
    acc_info = {
        "account_id": acc.id,
        "account_name": acc.name,
        "latest_balance": 0.0,
        "latest_transaction_id": None,
        "posted_at": None,
        "description": None
    }
    
    if tx:
        bal = Decimal(str(tx.balance))
        total += bal
        acc_info.update({
            "latest_balance": float(bal),
            "latest_transaction_id": tx.id,
            "posted_at": tx.posting_date.isoformat(),
            "description": tx.description
        })
    
    breakdown.append(acc_info)

return {
    "total_cash_balance": float(total),
    "currency": "USD",
    "accounts": breakdown,
    "provenance_note": "Derived from latest transaction per account"
}
"""
        self._create_fact_with_intent(
            id="money.cash_balance_breakdown",
            desc="Breakdown of cash balance by account with provenance",
            code=breakdown_code,
            data_type="dict",
            regex_patterns=[r"where did this number come from\??"],
            keywords=["provenance", "breakdown", "source"]
        )

    def _create_fact_with_intent(self, id, desc, code, data_type, regex_patterns, keywords):
        defn, _ = FactDefinition.objects.get_or_create(
            id=id,
            defaults={'description': desc, 'data_type': data_type}
        )
        
        ver, _ = FactDefinitionVersion.objects.update_or_create(
            fact_definition=defn,
            version=1,
            defaults={'code': code.strip(), 'status': 'approved', 'change_note': 'Level 0 Setup'}
        )
        
        IntentRecognizer.objects.update_or_create(
            fact_version=ver,
            defaults={'regex_patterns': regex_patterns, 'keywords': keywords}
        )

    def test_q1_cash_balance(self):
        """Test 'What is my current cash balance?'"""
        question = "What is my current cash balance?"
        response = self.engine.answer_question(question, user=self.user)
        
        # Expected total: 1000.00 + 2500.50 = 3500.50
        expected_total = 3500.50
        
        # Check text output (default formatting)
        self.assertIn(f"{expected_total:,.2f}", response['text'])
        
        # Verify FactInstance persistence
        # We need to find the latest FactInstance for this user/question context
        # Since engine creates a Question object, we can trace it if needed, 
        # but here we just check the latest instance for the fact.
        
        # Note: The engine uses the fact ID "money.cash_balance"
        # We need to find the version object first
        defn = FactDefinition.objects.get(id="money.cash_balance")
        ver = defn.versions.first()
        
        # Find instance
        # Note: context hash depends on user ID, so it should be unique for this user
        instance = FactInstance.objects.filter(fact_version=ver).latest('computed_at')
        
        self.assertEqual(instance.value['cash_balance'], expected_total)
        self.assertEqual(instance.value['currency'], 'USD')

    def test_q2_breakdown(self):
        """Test 'Where did this number come from?'"""
        question = "Where did this number come from?"
        response = self.engine.answer_question(question, user=self.user)
        
        expected_total = 3500.50
        
        # Check text output contains key info
        self.assertIn(f"{expected_total:,.2f}", response['text'])
        self.assertIn("Checking", response['text'])
        self.assertIn("Savings", response['text'])
        
        # Verify FactInstance structure
        defn = FactDefinition.objects.get(id="money.cash_balance_breakdown")
        ver = defn.versions.first()
        instance = FactInstance.objects.filter(fact_version=ver).latest('computed_at')
        
        data = instance.value
        self.assertEqual(data['total_cash_balance'], expected_total)
        self.assertEqual(len(data['accounts']), 2)
        
        # Verify specific account details
        checking = next(a for a in data['accounts'] if a['account_name'] == 'Checking')
        self.assertEqual(checking['latest_balance'], 1000.00)
        self.assertEqual(checking['description'], 'Latest Tx Acc1')
        
        savings = next(a for a in data['accounts'] if a['account_name'] == 'Savings')
        self.assertEqual(checking['latest_balance'], 1000.00)
        self.assertEqual(savings['latest_balance'], 2500.50)
