from django.core.management.base import BaseCommand
from facts.models import FactDefinitionVersion

class Command(BaseCommand):
    help = 'Fixes broken fact versions'

    def handle(self, *args, **options):
        # Fix current_balance
        versions = FactDefinitionVersion.objects.filter(fact_definition_id='current_balance', status='approved')
        for v in versions:
            updated = False
            if 'all_transactions' not in v.requires:
                v.requires = ['all_transactions']
                updated = True
            
            # Fix code to handle list instead of DataFrame assumption
            if "df['amount']" in v.code:
                v.code = "transactions = deps['all_transactions']\nreturn sum(t['amount'] for t in transactions)"
                updated = True
                
            if updated:
                v.save()
                self.stdout.write(self.style.SUCCESS(f"Fixed requirements and code for {v}"))
            else:
                self.stdout.write(f"{v} already has correct requirements and code")
