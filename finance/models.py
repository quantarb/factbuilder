from django.db import models
from django.contrib.auth.models import User

class Account(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return self.name

class BankTransaction(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    details = models.CharField(max_length=20)
    posting_date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=50)
    balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    check_or_slip_number = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.posting_date} - {self.description} - {self.amount}"

class CreditCardTransaction(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    card = models.CharField(max_length=10)
    transaction_date = models.DateField()
    post_date = models.DateField()
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    memo = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.transaction_date} - {self.description} - {self.amount}"
