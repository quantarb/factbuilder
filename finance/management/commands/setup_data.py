import os
import csv
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from finance.models import Account, BankTransaction, CreditCardTransaction
from facts.engine import QAEngine
from facts.models import FactDefinition, FactDefinitionVersion, IntentRecognizer
import pandas as pd
from django.db.models import Sum
from decimal import Decimal

class Command(BaseCommand):
    help = 'Sets up initial data: users, accounts, transactions, and facts.'

    def handle(self, *args: Any, **options: Any) -> None:
        admin_user = self.create_superuser()
        bank_account, credit_card_account = self.create_accounts(admin_user)
        
        # Assuming CSV files are in the project root
        bank_csv_path = 'bank_transactions.CSV'
        credit_card_csv_path = 'creditcard_transactions.CSV'
        
        if os.path.exists(bank_csv_path):
            self.import_bank_transactions(bank_account, bank_csv_path)
        else:
            self.stdout.write(self.style.WARNING(f"File not found: {bank_csv_path}"))

        if os.path.exists(credit_card_csv_path):
            self.import_credit_card_transactions(credit_card_account, credit_card_csv_path)
        else:
            self.stdout.write(self.style.WARNING(f"File not found: {credit_card_csv_path}"))
        
        self.setup_initial_facts()
        self.setup_level0_facts()
        self.setup_level1_facts()
        self.run_initial_questions(admin_user)

    def create_superuser(self) -> User:
        user, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com'})
        if created:
            user.set_password('admin123')
            user.is_superuser = True
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.SUCCESS("Superuser 'admin' created."))
        else:
            self.stdout.write("Superuser 'admin' already exists.")
        return user

    def create_accounts(self, user: User) -> Tuple[Account, Account]:
        bank_account, created = Account.objects.get_or_create(name='Chase Checking', defaults={'user': user})
        if created:
            self.stdout.write(f"Account '{bank_account.name}' created.")
        else:
            if not bank_account.user:
                bank_account.user = user
                bank_account.save()
            self.stdout.write(f"Account '{bank_account.name}' already exists.")

        credit_card_account, created = Account.objects.get_or_create(name='Chase Credit Card', defaults={'user': user})
        if created:
            self.stdout.write(f"Account '{credit_card_account.name}' created.")
        else:
            if not credit_card_account.user:
                credit_card_account.user = user
                credit_card_account.save()
            self.stdout.write(f"Account '{credit_card_account.name}' already exists.")
        
        return bank_account, credit_card_account

    def import_bank_transactions(self, account: Account, csv_path: str) -> None:
        if BankTransaction.objects.filter(account=account).exists():
            self.stdout.write(f"Bank transactions for {account.name} already exist. Skipping import.")
            return

        self.stdout.write(f"Importing bank transactions from {csv_path}...")
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            count = 0
            for row in reader:
                if not row: continue
                try:
                    posting_date = datetime.strptime(row[1], '%m/%d/%Y').date()
                    amount = float(row[3])
                    balance = float(row[5]) if row[5].strip() else None
                    
                    BankTransaction.objects.create(
                        account=account,
                        details=row[0],
                        posting_date=posting_date,
                        description=row[2],
                        amount=amount,
                        type=row[4],
                        balance=balance,
                        check_or_slip_number=row[6] if len(row) > 6 else None
                    )
                    count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing row {row}: {e}"))
            self.stdout.write(self.style.SUCCESS(f"Imported {count} bank transactions."))

    def import_credit_card_transactions(self, account: Account, csv_path: str) -> None:
        if CreditCardTransaction.objects.filter(account=account).exists():
            self.stdout.write(f"Credit card transactions for {account.name} already exist. Skipping import.")
            return

        self.stdout.write(f"Importing credit card transactions from {csv_path}...")
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            count = 0
            for row in reader:
                if not row: continue
                try:
                    transaction_date = datetime.strptime(row[1], '%m/%d/%Y').date()
                    post_date = datetime.strptime(row[2], '%m/%d/%Y').date()
                    amount = float(row[6])
                    
                    CreditCardTransaction.objects.create(
                        account=account,
                        card=row[0],
                        transaction_date=transaction_date,
                        post_date=post_date,
                        description=row[3],
                        category=row[4],
                        type=row[5],
                        amount=amount,
                        memo=row[7] if len(row) > 7 else None
                    )
                    count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing row {row}: {e}"))
            self.stdout.write(self.style.SUCCESS(f"Imported {count} credit card transactions."))

    def setup_initial_facts(self) -> None:
        self.stdout.write("Setting up initial dynamic facts...")
        
        facts = [
            {
                "id": "account_transactions",
                "description": "Transactions filtered by account context",
                "data_type": "dataframe",
                "requires": ["all_transactions"],
                "code": """
df = deps["all_transactions"]
if isinstance(df, list):
    df = pd.DataFrame(df)
    
account_name = context.get("account_name")
if account_name and not df.empty:
    return df[df['account__name'] == account_name]
return df
"""
            },
            {
                "id": "current_balance",
                "description": "Current balance for an account",
                "data_type": "scalar",
                "requires": [],
                "code": """
account_name = context.get("account_name")
user = context.get('user')

qs = BankTransaction.objects.filter(balance__isnull=False)

if user:
    qs = qs.filter(account__user=user)

if account_name:
    qs = qs.filter(account__name=account_name)
    
latest_tx = qs.order_by('-posting_date').first()
    
if latest_tx:
    return float(latest_tx.balance)
return 0.0
"""
            },
            {
                "id": "spending_by_category",
                "description": "Total spending grouped by category",
                "data_type": "dict",
                "requires": ["all_transactions"],
                "code": """
df = deps["all_transactions"]
if isinstance(df, list):
    df = pd.DataFrame(df)
    
if df.empty:
    return {}
# Filter for negative amounts (spending)
spending = df[df['amount'] < 0]
if spending.empty:
    return {}
return spending.groupby('category')['amount'].sum().abs().to_dict()
"""
            },
            {
                "id": "spending_on_date",
                "description": "Total spending on a specific date",
                "data_type": "scalar",
                "requires": ["all_transactions"],
                "code": """
df = deps["all_transactions"]
if isinstance(df, list):
    df = pd.DataFrame(df)

target_date = context.get("date")
if not target_date or df.empty:
    return 0.0
    
# Ensure target_date is a date object
if isinstance(target_date, str):
    target_date = pd.to_datetime(target_date).date()
    
# Convert date column to date objects if they are strings
if df['date'].dtype == 'object':
    df['date'] = pd.to_datetime(df['date']).dt.date

daily_txs = df[df['date'] == target_date]
# Sum negative amounts
spent = daily_txs[daily_txs['amount'] < 0]['amount'].sum()
return abs(spent)
"""
            }
        ]
        
        for f in facts:
            defn, _ = FactDefinition.objects.get_or_create(
                id=f['id'],
                defaults={
                    'description': f['description'],
                    'data_type': f['data_type'],
                    'is_active': True
                }
            )
            
            # Create version if not exists
            if not defn.versions.exists():
                FactDefinitionVersion.objects.create(
                    fact_definition=defn,
                    version=1,
                    requires=f['requires'],
                    code=f['code'].strip(),
                    status='approved',
                    change_note="Initial setup"
                )
            else:
                # Update existing version code for development iteration
                v = defn.versions.first()
                v.code = f['code'].strip()
                v.save()

        self.stdout.write(self.style.SUCCESS(f"Ensured {len(facts)} initial facts exist."))

    def setup_level0_facts(self) -> None:
        self.stdout.write("Setting up Level 0 Facts & Intents...")

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

    def setup_level1_facts(self) -> None:
        self.stdout.write("Setting up Level 1 Facts & Intents...")

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
        self._create_fact_with_intent(
            id="money.balance_at_date",
            desc="Balance at a specific date",
            code=code_balance_at_date,
            data_type="dict",
            regex_patterns=[r"what was my balance (on )?(?P<date>yesterday|[\w\s]+)\??"],
            keywords=["balance", "yesterday"]
        )

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
        self._create_fact_with_intent(
            id="money.next_paycheck",
            desc="Next estimated paycheck",
            code=code_next_paycheck,
            data_type="dict",
            regex_patterns=[],
            keywords=[]
        )

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
        self._create_fact_with_intent(
            id="money.obligations",
            desc="Recurring obligations inferred from history",
            code=code_obligations,
            data_type="list",
            regex_patterns=[],
            keywords=[]
        )

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
        self._create_fact_with_intent(
            id="money.obligations_due_before_paycheck",
            desc="Bills due before next paycheck",
            code=code_obligations_due,
            data_type="list",
            regex_patterns=[r"what bills are due before my next paycheck\??"],
            keywords=["bills", "due"],
            requires=['money.next_paycheck', 'money.obligations']
        )

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
        self._create_fact_with_intent(
            id="money.spoken_for",
            desc="Money already committed to bills",
            code=code_spoken_for,
            data_type="dict",
            regex_patterns=[r"how much money is (already )?spoken for\??"],
            keywords=["spoken for"],
            requires=['money.obligations_due_before_paycheck']
        )

        # 6. money.spending_time_range (Level 1 - Time-based)
        code_spending_time_range = """
user = context.get('user')
start_date_str = context.get('start_date')
end_date_str = context.get('end_date')
period = context.get('period') # yesterday, last_week, last_month

today = date.today()
start_date = None
end_date = today

if period == 'yesterday':
    start_date = today - timedelta(days=1)
    end_date = start_date
elif period == 'last_week':
    start_date = today - timedelta(days=7)
elif period == 'last_month':
    start_date = today - timedelta(days=30)
elif start_date_str:
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except:
        pass

if not start_date:
    return {"error": "Invalid date range"}

accounts = Account.objects.filter(user=user)
total_spent = Decimal('0.00')
txs = []

# Bank Transactions (Outflows)
bank_txs = BankTransaction.objects.filter(
    account__in=accounts,
    posting_date__gte=start_date,
    posting_date__lte=end_date,
    amount__lt=0
)

for tx in bank_txs:
    total_spent += abs(tx.amount)
    txs.append({
        "date": tx.posting_date.isoformat(),
        "description": tx.description,
        "amount": float(abs(tx.amount)),
        "source": "Bank"
    })

# Credit Card Transactions (Outflows/Purchases)
cc_txs = CreditCardTransaction.objects.filter(
    account__in=accounts,
    transaction_date__gte=start_date,
    transaction_date__lte=end_date,
    amount__gt=0 # CC positive is usually charge, but let's check model. Usually positive amount is charge.
)

for tx in cc_txs:
    total_spent += tx.amount
    txs.append({
        "date": tx.transaction_date.isoformat(),
        "description": tx.description,
        "amount": float(tx.amount),
        "source": "Credit Card"
    })

return {
    "total_spent": float(total_spent),
    "currency": "USD",
    "period": period or f"{start_date} to {end_date}",
    "transactions": sorted(txs, key=lambda x: x['date'], reverse=True)
}
"""
        self._create_fact_with_intent(
            id="money.spending_time_range",
            desc="Spending over a time range",
            code=code_spending_time_range,
            data_type="dict",
            regex_patterns=[
                r"how much did i spend (?P<period>yesterday|last week|last month)\??",
                r"how much did i spend (from )?(?P<start_date>\d{4}-\d{2}-\d{2})( to )?(?P<end_date>\d{4}-\d{2}-\d{2})?\??"
            ],
            keywords=["spend", "spent", "yesterday", "last week"]
        )

        # 7. money.income_time_range (Level 1 - Direction-based)
        code_income_time_range = """
user = context.get('user')
days = context.get('days', 30)
if isinstance(days, str) and days.isdigit():
    days = int(days)

today = date.today()
start_date = today - timedelta(days=days)

accounts = Account.objects.filter(user=user)
total_income = Decimal('0.00')
txs = []

# Bank Transactions (Inflows)
bank_txs = BankTransaction.objects.filter(
    account__in=accounts,
    posting_date__gte=start_date,
    amount__gt=0
)

for tx in bank_txs:
    total_income += tx.amount
    txs.append({
        "date": tx.posting_date.isoformat(),
        "description": tx.description,
        "amount": float(tx.amount)
    })

return {
    "total_income": float(total_income),
    "currency": "USD",
    "period": f"Last {days} days",
    "transactions": sorted(txs, key=lambda x: x['date'], reverse=True)
}
"""
        self._create_fact_with_intent(
            id="money.income_time_range",
            desc="Income over time range",
            code=code_income_time_range,
            data_type="dict",
            regex_patterns=[r"how much money came in (over|in) the last (?P<days>\d+) days\??"],
            keywords=["income", "came in"]
        )

        # 8. money.merchant_spending_refusal (Level 1 - Explicit Refusal)
        code_merchant_refusal = """
return "This question cannot be answered yet because merchant information does not exist."
"""
        self._create_fact_with_intent(
            id="money.merchant_spending_refusal",
            desc="Refusal for merchant-based questions",
            code=code_merchant_refusal,
            data_type="scalar",
            regex_patterns=[
                r"how much did i spend at (?P<merchant>[\w\s]+)( last month| yesterday)?\??",
                r"how much do i spend at (?P<merchant>[\w\s]+)\??",
                r"what merchants? do i spend the most money at\??"
            ],
            keywords=["merchant", "amazon", "starbucks", "spend at"]
        )

    def _create_fact_with_intent(self, id: str, desc: str, code: str, data_type: str, regex_patterns: List[str], keywords: List[str], requires: Optional[List[str]] = None) -> None:
        defn, _ = FactDefinition.objects.get_or_create(
            id=id,
            defaults={'description': desc, 'data_type': data_type}
        )
        
        ver, _ = FactDefinitionVersion.objects.update_or_create(
            fact_definition=defn,
            version=1,
            defaults={
                'code': code.strip(), 
                'status': 'approved', 
                'change_note': 'Setup',
                'requires': requires or []
            }
        )
        
        IntentRecognizer.objects.update_or_create(
            fact_version=ver,
            defaults={'regex_patterns': regex_patterns, 'keywords': keywords}
        )

    def run_initial_questions(self, user: User) -> None:
        self.stdout.write("\n--- Running Initial QA to Build Taxonomy Facts ---")
        engine = QAEngine()
        
        questions = [
            "What is my current cash balance?",
            "Where did this number come from?",
            "What was my balance yesterday?",
            "What bills are due before my next paycheck?",
            "How much money is already spoken for?",
            "How much did I spend yesterday?",
            "How much money came in over the last 30 days?",
            "How much did I spend at Amazon last month?"
        ]
        
        for q_text in questions:
            self.stdout.write(f"\nQuestion: {q_text}")
            answer = engine.answer_question(q_text, user=user)
            self.stdout.write(f"Answer: {answer}")
