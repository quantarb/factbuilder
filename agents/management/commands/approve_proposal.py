from django.core.management.base import BaseCommand
from agents.models import TaxonomyProposal
from facts.models import DynamicFact

class Command(BaseCommand):
    help = 'Approves a pending taxonomy proposal and converts it into a DynamicFact.'

    def add_arguments(self, parser):
        parser.add_argument('proposal_id', type=int, help='The ID of the proposal to approve')

    def handle(self, *args, **options):
        proposal_id = options['proposal_id']
        
        try:
            proposal = TaxonomyProposal.objects.get(id=proposal_id)
        except TaxonomyProposal.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Proposal with ID {proposal_id} not found."))
            return

        if proposal.status != 'pending':
            self.stdout.write(self.style.WARNING(f"Proposal {proposal_id} is already {proposal.status}."))
            return

        self.stdout.write(f"Approving proposal: {proposal.question}")
        self.stdout.write(f"Fact ID: {proposal.proposed_fact_id}")
        self.stdout.write(f"Logic:\n{proposal.proposed_logic}")
        
        # Create the DynamicFact
        try:
            DynamicFact.objects.create(
                id=proposal.proposed_fact_id,
                description=f"Auto-generated for: {proposal.question}",
                kind="computed",
                data_type="scalar", # Defaulting to scalar
                requires=["all_transactions"],
                code=proposal.proposed_logic,
                is_active=True
            )
            
            # Update proposal status
            proposal.status = 'approved'
            proposal.save()
            
            self.stdout.write(self.style.SUCCESS(f"Successfully approved proposal {proposal_id}. The system can now answer this question."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to create DynamicFact: {e}"))
