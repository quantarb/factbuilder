from django.contrib import admin
from .models import (
    Entity, EntityAlias, RecurrenceCandidate, RecurrenceCandidateEvidence,
    RecurringExpense, RecurringIncome, UserConfirmationEvent,
    ReservePolicy, ReserveInstance
)

class EntityAliasInline(admin.TabularInline):
    model = EntityAlias
    extra = 1

@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'created_at')
    search_fields = ('name', 'category')
    inlines = [EntityAliasInline]

class EvidenceInline(admin.TabularInline):
    model = RecurrenceCandidateEvidence
    extra = 0
    readonly_fields = ('bank_transaction', 'credit_card_transaction')

@admin.register(RecurrenceCandidate)
class RecurrenceCandidateAdmin(admin.ModelAdmin):
    list_display = ('entity', 'type', 'predicted_amount', 'predicted_periodicity', 'confidence', 'status')
    list_filter = ('status', 'type', 'predicted_periodicity')
    inlines = [EvidenceInline]
    actions = ['confirm_candidates']

    def confirm_candidates(self, request, queryset):
        for candidate in queryset:
            if candidate.status == 'pending':
                # Logic to confirm would go here, but usually requires user input for final details
                # For admin action, we might just mark status, but creating the RecurringExpense is better done via a proper view/service
                pass
    confirm_candidates.short_description = "Mark selected candidates as confirmed (Metadata only)"

@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'periodicity', 'next_due_date', 'is_active')
    list_filter = ('periodicity', 'is_active')

@admin.register(RecurringIncome)
class RecurringIncomeAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'periodicity', 'next_expected_date', 'is_active')

@admin.register(UserConfirmationEvent)
class UserConfirmationEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'candidate', 'action', 'timestamp')
    readonly_fields = ('user', 'candidate', 'action', 'timestamp', 'original_values', 'final_values')

@admin.register(ReservePolicy)
class ReservePolicyAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'target_amount', 'percentage_of_income', 'priority')

@admin.register(ReserveInstance)
class ReserveInstanceAdmin(admin.ModelAdmin):
    list_display = ('policy', 'amount', 'date')
