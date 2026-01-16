import os
import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from finance.models import Account, BankTransaction, CreditCardTransaction
from facts.engine import QAEngine
from facts.models import DynamicFact
import pandas as pd
from django.db.models import Sum

class Command(BaseCommand):
    help = 'Sets up initial data: users, accounts, transactions, and facts.'

    def handle(self, *args, **options):
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
        self.run_initial_questions(admin_user)

    def create_superuser(self):
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

    def create_accounts(self, user):
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

    def import_bank_transactions(self, account, csv_path):
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

    def import_credit_card_transactions(self, account, csv_path):
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

    def setup_initial_facts(self):
        self.stdout.write("Setting up initial dynamic facts...")
        
        facts = [
            {
                "id": "account_transactions",
                "description": "Transactions filtered by account context",
                "kind": "computed",
                "data_type": "dataframe",
                "requires": ["all_transactions"],
                "code": """
df = deps["all_transactions"]
account_name = context.get("account_name")
if account_name:
    return df[df['account__name'] == account_name]
return df
"""
            },
            {
                "id": "current_balance",
                "description": "Current balance for an account",
                "kind": "computed",
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
                "kind": "computed",
                "data_type": "dict",
                "requires": ["all_transactions"],
                "code": """
df = deps["all_transactions"]
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
                "kind": "computed",
                "data_type": "scalar",
                "requires": ["all_transactions"],
                "code": """
df = deps["all_transactions"]
target_date = context.get("date")
if not target_date:
    return 0.0
    
# Ensure target_date is a date object
if isinstance(target_date, str):
    target_date = pd.to_datetime(target_date).date()
    
daily_txs = df[df['date'] == target_date]
# Sum negative amounts
spent = daily_txs[daily_txs['amount'] < 0]['amount'].sum()
return abs(spent)
"""
            }
        ]
        
        for f in facts:
            DynamicFact.objects.get_or_create(
                id=f['id'],
                defaults={
                    'description': f['description'],
                    'kind': f['kind'],
                    'data_type': f['data_type'],
                    'requires': f['requires'],
                    'code': f['code'].strip(),
                    'is_active': True
                }
            )
        self.stdout.write(self.style.SUCCESS(f"Ensured {len(facts)} initial facts exist."))

    def run_initial_questions(self, user):
        self.stdout.write("\n--- Running Initial QA to Build Taxonomy Facts ---")
        engine = QAEngine()
        
        questions = [
            "What is the current balance of Chase Checking?",
            "How much did I spend on 2026-01-02?",
            "How much did I spend on 2025-12-31?",
            "What is my spending by category?",
        ]
        
        for q_text in questions:
            self.stdout.write(f"\nQuestion: {q_text}")
            answer = engine.answer_question(q_text, user=user)
            self.stdout.write(f"Answer: {answer}")
