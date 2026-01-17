from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from finance.models import Account, BankTransaction
from frugal.models import (
    Entity, RecurrenceCandidate, RecurrenceCandidateEvidence, 
    RecurringExpense, UserConfirmationEvent
)

class RecurrenceInferenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='testuser')
        self.account = Account.objects.create(name='Checking', user=self.user)
        self.entity = Entity.objects.create(name='Netflix')
        
        # Create some transactions
        self.tx1 = BankTransaction.objects.create(
            account=self.account,
            details='DEBIT',
            posting_date=timezone.now().date(),
            description='NETFLIX.COM',
            amount=Decimal('15.99'),
            type='DEBIT'
        )

    def test_candidate_creation_requires_evidence(self):
        """
        Test that we can create a candidate and link evidence.
        """
        candidate = RecurrenceCandidate.objects.create(
            user=self.user,
            entity=self.entity,
            type='expense',
            predicted_amount=Decimal('15.99'),
            predicted_periodicity='monthly',
            next_expected_date=timezone.now().date(),
            confidence=0.9
        )
        
        evidence = RecurrenceCandidateEvidence.objects.create(
            candidate=candidate,
            bank_transaction=self.tx1
        )
        
        self.assertEqual(candidate.evidence.count(), 1)
        self.assertEqual(candidate.evidence.first().bank_transaction, self.tx1)

    def test_confirmation_flow(self):
        """
        Test confirming a candidate creates a RecurringExpense.
        """
        candidate = RecurrenceCandidate.objects.create(
            user=self.user,
            entity=self.entity,
            type='expense',
            predicted_amount=Decimal('15.99'),
            predicted_periodicity='monthly',
            next_expected_date=timezone.now().date(),
            confidence=0.9,
            status='pending'
        )
        
        # Simulate User Action
        candidate.status = 'confirmed'
        candidate.save()
        
        expense = RecurringExpense.objects.create(
            user=self.user,
            entity=candidate.entity,
            name=candidate.entity.name,
            amount=candidate.predicted_amount,
            periodicity=candidate.predicted_periodicity,
            next_due_date=candidate.next_expected_date,
            source_candidate=candidate
        )
        
        UserConfirmationEvent.objects.create(
            user=self.user,
            candidate=candidate,
            action='confirm'
        )
        
        self.assertEqual(RecurringExpense.objects.count(), 1)
        self.assertEqual(expense.source_candidate, candidate)
        self.assertEqual(expense.amount, Decimal('15.99'))

    def test_transactions_do_not_imply_recurring_automatically(self):
        """
        Ensure that merely having transactions does not create RecurringExpense
        records without the candidate/confirmation step.
        """
        # We have tx1 from setUp
        self.assertEqual(BankTransaction.objects.count(), 1)
        self.assertEqual(RecurringExpense.objects.count(), 0)
        self.assertEqual(RecurrenceCandidate.objects.count(), 0)
