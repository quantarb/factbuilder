from django.core.management.base import BaseCommand
from agents.models import TaxonomyProposal

class Command(BaseCommand):
    help = 'Lists all pending taxonomy proposals.'

    def handle(self, *args, **options):
        proposals = TaxonomyProposal.objects.filter(status='pending')
        
        if not proposals.exists():
            self.stdout.write("No pending proposals.")
            return

        self.stdout.write(f"{'ID':<5} {'Fact ID':<25} {'Question':<50}")
        self.stdout.write("-" * 80)
        
        for p in proposals:
            self.stdout.write(f"{p.id:<5} {p.proposed_fact_id:<25} {p.question[:47] + '...' if len(p.question) > 47 else p.question:<50}")
