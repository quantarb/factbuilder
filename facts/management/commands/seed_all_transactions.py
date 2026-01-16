from django.core.management.base import BaseCommand
from facts.models import FactDefinition, FactDefinitionVersion

class Command(BaseCommand):
    help = 'Seeds the all_transactions fact'

    def handle(self, *args, **options):
        fact_id = 'all_transactions'
        
        # 1. Create Definition
        defn, created = FactDefinition.objects.get_or_create(
            id=fact_id,
            defaults={
                'description': 'All bank and credit card transactions for the user',
                'data_type': FactDefinition.FactValueType.LIST
            }
        )
        
        if not created and defn.data_type != FactDefinition.FactValueType.LIST:
            defn.data_type = FactDefinition.FactValueType.LIST
            defn.save()
            self.stdout.write(self.style.WARNING(f"Updated data_type for {fact_id}"))

        # 2. Create Version
        code = """
user = context.get('user')
bank_qs = BankTransaction.objects.all()
cc_qs = CreditCardTransaction.objects.all()

if user:
    bank_qs = bank_qs.filter(account__user=user)
    cc_qs = cc_qs.filter(account__user=user)

bank_txs = list(bank_qs.values('posting_date', 'description', 'amount', 'type', 'account__name'))
for tx in bank_txs:
    tx['date'] = tx.pop('posting_date').isoformat()
    tx['category'] = 'Bank Transaction'
    tx['amount'] = float(tx['amount'])
    
cc_txs = list(cc_qs.values('transaction_date', 'description', 'amount', 'category', 'type', 'account__name'))
for tx in cc_txs:
    tx['date'] = tx.pop('transaction_date').isoformat()
    tx['amount'] = float(tx['amount'])

return bank_txs + cc_txs
"""
        
        # Check if version exists
        existing = FactDefinitionVersion.objects.filter(
            fact_definition=defn,
            status='approved'
        ).first()
        
        if not existing:
            FactDefinitionVersion.objects.create(
                fact_definition=defn,
                version=1,
                code=code.strip(),
                requires=[],
                status='approved',
                change_note="Initial seed"
            )
            self.stdout.write(self.style.SUCCESS(f"Seeded {fact_id} v1"))
        else:
            self.stdout.write(f"{fact_id} already has an approved version.")
