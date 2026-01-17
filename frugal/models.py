from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from finance.models import BankTransaction, CreditCardTransaction

class Entity(models.Model):
    """
    Represents a real-world entity (merchant, employer, person)
    abstracted from raw transaction descriptions.
    """
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class EntityAlias(models.Model):
    """
    Maps raw transaction descriptions to a canonical Entity.
    """
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='aliases')
    raw_description_pattern = models.CharField(max_length=255, help_text="Regex or exact match string")
    is_regex = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.raw_description_pattern} -> {self.entity.name}"

class RecurrenceCandidate(models.Model):
    """
    A hypothesis about a recurring expense or income.
    Must be confirmed by the user before becoming a 'fact'.
    """
    TYPE_CHOICES = [
        ('expense', 'Expense'),
        ('income', 'Income'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    # Inferred properties
    predicted_amount = models.DecimalField(max_digits=10, decimal_places=2)
    predicted_periodicity = models.CharField(max_length=50, help_text="e.g., monthly, weekly")
    next_expected_date = models.DateField()
    
    confidence = models.FloatField(help_text="0.0 to 1.0 score of inference certainty")
    status = models.CharField(
        max_length=20, 
        choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('rejected', 'Rejected')],
        default='pending'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Candidate {self.type}: {self.predicted_amount} ({self.status})"

class RecurrenceCandidateEvidence(models.Model):
    """
    Links a candidate to the specific transactions that generated the hypothesis.
    """
    candidate = models.ForeignKey(RecurrenceCandidate, on_delete=models.CASCADE, related_name='evidence')
    bank_transaction = models.ForeignKey(BankTransaction, on_delete=models.CASCADE, null=True, blank=True)
    credit_card_transaction = models.ForeignKey(CreditCardTransaction, on_delete=models.CASCADE, null=True, blank=True)
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.bank_transaction and not self.credit_card_transaction:
            raise ValidationError("Must link to either a bank or credit card transaction")

class RecurringExpense(models.Model):
    """
    A confirmed recurring expense.
    This is Level 2 knowledge (Inferred Structure -> Confirmed Fact).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    periodicity = models.CharField(max_length=50) # e.g. 'monthly', 'yearly'
    next_due_date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    # Link back to the candidate that spawned this (if any)
    source_candidate = models.OneToOneField(RecurrenceCandidate, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.amount} ({self.periodicity})"

class RecurringIncome(models.Model):
    """
    A confirmed recurring income source.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    periodicity = models.CharField(max_length=50)
    next_expected_date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    source_candidate = models.OneToOneField(RecurrenceCandidate, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.amount} ({self.periodicity})"

class UserConfirmationEvent(models.Model):
    """
    Audit log of user decisions on candidates.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    candidate = models.ForeignKey(RecurrenceCandidate, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=[('confirm', 'Confirm'), ('reject', 'Reject'), ('edit', 'Edit')])
    timestamp = models.DateTimeField(default=timezone.now)
    original_values = models.JSONField(null=True, blank=True) # Snapshot before edit
    final_values = models.JSONField(null=True, blank=True)    # Snapshot after edit

class ReservePolicy(models.Model):
    """
    Level 3: Available-to-spend logic.
    Defines a rule for setting aside money (e.g., 'Emergency Fund', 'Tax Reserve').
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    percentage_of_income = models.FloatField(null=True, blank=True, help_text="0.0 to 100.0")
    priority = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ReserveInstance(models.Model):
    """
    Actual allocation of funds to a policy at a point in time.
    """
    policy = models.ForeignKey(ReservePolicy, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    
    def __str__(self):
        return f"{self.policy.name}: {self.amount}"
