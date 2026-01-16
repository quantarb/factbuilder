from django.contrib import admin
from .models import FactDefinition, FactDefinitionVersion, FactInstance, Question, Answer

@admin.register(FactDefinition)
class FactDefinitionAdmin(admin.ModelAdmin):
    list_display = ('id', 'description', 'is_active', 'updated_at')
    search_fields = ('id', 'description')

@admin.register(FactDefinitionVersion)
class FactDefinitionVersionAdmin(admin.ModelAdmin):
    list_display = ('fact_definition', 'version', 'status', 'created_at')
    list_filter = ('status', 'fact_definition')
    ordering = ('-created_at',)

@admin.register(FactInstance)
class FactInstanceAdmin(admin.ModelAdmin):
    list_display = ('fact_version', 'status', 'computed_at')
    list_filter = ('status', 'fact_version__fact_definition')
    readonly_fields = ('context_hash', 'computed_at')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'user', 'created_at')

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'text', 'created_at')
    filter_horizontal = ('facts_used',)
