from django.test import TestCase
from django.contrib.auth.models import User
from finance.models import Account, BankTransaction
from facts.engine import QAEngine
from facts.models import FactDefinition, FactDefinitionVersion, IntentRecognizer, FactInstance
from decimal import Decimal
from datetime import date, timedelta, datetime

class Level1TimeObligationsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.acc = Account.objects.create(name='Checking', user=self.user)
        self.engine = QAEngine()
        
        # Setup Facts
        self.setup_level1_facts()

        # Create Data relative to TODAY to ensure "yesterday" and "upcoming" logic works
        today = date.today()
        
        # 1. Balance History
        # 2 days ago: Balance 1000
        BankTransaction.objects.create(
            account=self.acc,
            details='DEBIT',
            posting_date=today - timedelta(days=2),
            description='Old Tx',
            amount=-50.00,
            type='DEBIT',
            balance=1000.00
        )
        # Yesterday: Balance 900
        BankTransaction.objects.create(
            account=self.acc,
            details='DEBIT',
            posting_date=today - timedelta(days=1),
            description='Yesterday Tx',
            amount=-100.00,
            type='DEBIT',
            balance=900.00
        )
        # Today: Balance 850
        BankTransaction.objects.create(
            account=self.acc,
            details='DEBIT',
            posting_date=today,
            description='Today Tx',
            amount=-50.00,
            type='DEBIT',
            balance=850.00
        )

        # 2. Income (for Paycheck detection)
        # Paycheck 10 days ago (Bi-weekly cycle -> Next in 4 days)
        BankTransaction.objects.create(
            account=self.acc,
            details='CREDIT',
            posting_date=today - timedelta(days=10),
            description='Payroll Deposit',
            amount=2000.00,
            type='CREDIT',
            balance=3000.00 # Balance doesn't strictly need to match for these tests unless we check consistency
        )

        # 3. Bills (Recurring)
        # Rent: Paid 28 days ago (Due in ~2 days)
        BankTransaction.objects.create(
            account=self.acc,
            details='DEBIT',
            posting_date=today - timedelta(days=28),
            description='Landlord Rent',
            amount=-1200.00,
            type='DEBIT',
            balance=1000.00
        )
        # Utility: Paid 15 days ago (Due in ~15 days -> After next paycheck)
        BankTransaction.objects.create(
            account=self.acc,
            details='DEBIT',
            posting_date=today - timedelta(days=15),
            description='Electric Co',
            amount=-100.00,
            type='DEBIT',
            balance=900.00
        )

    def setup_level1_facts(self):
        # This mirrors what we will put in setup_data.py
        # We define it here to make the test self-contained or we can import from setup_data if we refactor.
        # For now, I'll define the minimal versions needed for the test to pass, 
        # then I'll copy the code to setup_data.py.
        
        # 1. money.balance_at_date
        code_balance_at_date = """
target_date_str = context.get('date')
target_date = None

if target_date_str == 'yesterday':
    target_date = date.today() - timedelta(days=1)
elif target_date_str:
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except:
        pass

if not target_date:
    return {"error": "Invalid date"}

user = context.get('user')
accounts = Account.objects.filter(user=user)
total = Decimal('0.00')

for acc in accounts:
    # Find latest transaction on or before target_date
    tx = BankTransaction.objects.filter(
        account=acc, 
        posting_date__lte=target_date,
        balance__isnull=False
    ).order_by('-posting_date', '-id').first()
    
    if tx:
        total += Decimal(str(tx.balance))

return {
    "date": target_date.isoformat(),
    "balance": float(total),
    "currency": "USD"
}
"""
        self._create_fact("money.balance_at_date", code_balance_at_date, 
                          [r"what was my balance (on )?(?P<date>yesterday|[\w\s]+)\??"], ["balance", "yesterday"])

        # 2. money.next_paycheck
        code_next_paycheck = """
user = context.get('user')
accounts = Account.objects.filter(user=user)

# Find latest payroll
latest_pay = BankTransaction.objects.filter(
    account__in=accounts,
    amount__gt=0,
    description__icontains='Payroll'
).order_by('-posting_date').first()

if not latest_pay:
    return None

# Assume bi-weekly for MVP
last_date = latest_pay.posting_date
next_date = last_date + timedelta(days=14)
days_until = (next_date - date.today()).days

return {
    "next_paycheck_date": next_date.isoformat(),
    "days_until": days_until,
    "estimated_amount": float(latest_pay.amount)
}
"""
        self._create_fact("money.next_paycheck", code_next_paycheck, [], [])

        # 3. money.obligations (Inferred Bills)
        code_obligations = """
# Simple heuristic: Look for specific keywords in past 60 days
keywords = {'Rent': 30, 'Electric': 30, 'Netflix': 30, 'Internet': 30}
user = context.get('user')
accounts = Account.objects.filter(user=user)

obligations = []
today = date.today()

for kw, period in keywords.items():
    # Find last occurrence
    tx = BankTransaction.objects.filter(
        account__in=accounts,
        description__icontains=kw,
        amount__lt=0
    ).order_by('-posting_date').first()
    
    if tx:
        # Project next date
        # If paid on day X, next is X + period
        next_due = tx.posting_date + timedelta(days=period)
        if next_due < today:
             # If overdue, maybe it's due today or we missed it. 
             # For simplicity, let's say it's due today if calculated in past
             next_due = today
             
        obligations.append({
            "name": kw,
            "amount": abs(float(tx.amount)),
            "due_date": next_due.isoformat()
        })

return sorted(obligations, key=lambda x: x['due_date'])
"""
        self._create_fact("money.obligations", code_obligations, [], [])

        # 4. money.obligations_due_before_paycheck
        code_obligations_due = """
paycheck = deps['money.next_paycheck']
all_obligations = deps['money.obligations']

if not paycheck:
    return []

cutoff = datetime.strptime(paycheck['next_paycheck_date'], '%Y-%m-%d').date()
today = date.today()

due = []
for ob in all_obligations:
    d = datetime.strptime(ob['due_date'], '%Y-%m-%d').date()
    if today <= d < cutoff:
        due.append(ob)

return due
"""
        self._create_fact("money.obligations_due_before_paycheck", code_obligations_due, 
                          [r"what bills are due before my next paycheck\??"], ["bills", "due"],
                          requires=['money.next_paycheck', 'money.obligations'])

        # 5. money.spoken_for
        code_spoken_for = """
due_bills = deps['money.obligations_due_before_paycheck']
total = sum(item['amount'] for item in due_bills)
return {
    "amount": total,
    "currency": "USD",
    "breakdown": due_bills
}
"""
        self._create_fact("money.spoken_for", code_spoken_for, 
                          [r"how much money is (already )?spoken for\??"], ["spoken for"],
                          requires=['money.obligations_due_before_paycheck'])


    def _create_fact(self, id, code, regexes, keywords, requires=None):
        defn, _ = FactDefinition.objects.get_or_create(
            id=id,
            defaults={'description': 'Test Fact', 'data_type': 'dict'}
        )
        ver, _ = FactDefinitionVersion.objects.update_or_create(
            fact_definition=defn,
            version=1,
            defaults={
                'code': code.strip(), 
                'status': 'approved', 
                'requires': requires or []
            }
        )
        IntentRecognizer.objects.update_or_create(
            fact_version=ver,
            defaults={'regex_patterns': regexes, 'keywords': keywords}
        )

    def test_balance_yesterday(self):
        q = "What was my balance yesterday?"
        resp = self.engine.answer_question(q, user=self.user)
        # Yesterday balance should be 900.00
        self.assertIn("900.0", resp['text'])

    def test_bills_due_before_paycheck(self):
        q = "What bills are due before my next paycheck?"
        resp = self.engine.answer_question(q, user=self.user)
        
        # Paycheck is in 4 days.
        # Rent (paid 28 days ago) -> Due in 2 days (30 day cycle). Should be included.
        # Electric (paid 15 days ago) -> Due in 15 days. Should NOT be included.
        
        self.assertIn("Rent", resp['text'])
        self.assertNotIn("Electric", resp['text'])

    def test_spoken_for(self):
        q = "How much money is already spoken for?"
        resp = self.engine.answer_question(q, user=self.user)
        
        # Should be sum of Rent (1200)
        self.assertIn("1,200.00", resp['text'])
