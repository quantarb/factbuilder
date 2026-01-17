from django.test import TestCase
from agents.models import TaxonomyProposal
from facts.models import FactDefinition, FactDefinitionVersion

class TaxonomyProposalTests(TestCase):
    def test_approve_proposal_expression(self):
        # Create a proposal for a simple expression fact
        proposal = TaxonomyProposal.objects.create(
            question="What is 1+1?",
            feasibility_analysis="Feasible",
            proposed_fact_id="simple_math",
            proposed_logic="1 + 1",
            proposed_logic_type="expression",
            proposed_data_type="scalar",
            test_cases=[{"context": {}, "expected_type": "scalar", "expected_contains": "2"}]
        )
        
        proposal.approve()
        
        self.assertEqual(proposal.status, 'approved')
        self.assertIsNotNone(proposal.created_version)
        self.assertEqual(proposal.created_version.logic_type, 'expression')
        
        # Verify FactDefinition and Version created
        defn = FactDefinition.objects.get(id="simple_math")
        self.assertEqual(defn.data_type, 'scalar')
        
        ver = FactDefinitionVersion.objects.get(fact_definition=defn, version=1)
        self.assertEqual(ver.code, "1 + 1")

    def test_approve_proposal_invalid_test(self):
        # Proposal with failing test
        proposal = TaxonomyProposal.objects.create(
            question="Bad math",
            feasibility_analysis="Feasible",
            proposed_fact_id="bad_math",
            proposed_logic="1 + 1",
            proposed_logic_type="expression",
            proposed_data_type="scalar",
            test_cases=[{"context": {}, "expected_contains": "3"}] # Expect 3, but logic gives 2
        )
        
        proposal.approve()
        
        self.assertEqual(proposal.status, 'pending')
        self.assertIn("Test 0 failed", proposal.approval_error)
