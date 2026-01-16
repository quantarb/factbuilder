from django.contrib import admin
from .models import FactType, Fact, Question, Answer

@admin.register(FactType)
class FactTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(Fact)
class FactAdmin(admin.ModelAdmin):
    list_display = ('fact_type', 'value', 'created_at')
    list_filter = ('fact_type',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'user', 'created_at')

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'text', 'created_at')
    filter_horizontal = ('facts_used',)
