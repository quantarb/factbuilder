from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django import forms
from django.contrib import messages
import csv
import io
from datetime import datetime
from .models import BankTransaction, CreditCardTransaction, Account

class CsvImportForm(forms.Form):
    csv_file = forms.FileField()
    account = forms.ModelChoiceField(queryset=Account.objects.all())

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ('posting_date', 'description', 'amount', 'type', 'balance', 'account')
    change_list_template = "admin/bank_transaction_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            form = CsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES["csv_file"]
                account = form.cleaned_data["account"]
                decoded_file = csv_file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                reader = csv.reader(io_string)
                next(reader)  # Skip header
                
                for row in reader:
                    if not row: continue
                    # Expected format: Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #
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
                    except Exception as e:
                        messages.error(request, f"Error processing row {row}: {e}")
                        continue
                
                messages.success(request, "CSV file imported successfully")
                return redirect("..")
            
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)

@admin.register(CreditCardTransaction)
class CreditCardTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'description', 'amount', 'category', 'type', 'account')
    change_list_template = "admin/credit_card_transaction_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            form = CsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES["csv_file"]
                account = form.cleaned_data["account"]
                decoded_file = csv_file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                reader = csv.reader(io_string)
                next(reader)  # Skip header
                
                for row in reader:
                    if not row: continue
                    # Expected format: Card,Transaction Date,Post Date,Description,Category,Type,Amount,Memo
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
                    except Exception as e:
                        messages.error(request, f"Error processing row {row}: {e}")
                        continue
                
                messages.success(request, "CSV file imported successfully")
                return redirect("..")
            
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)
