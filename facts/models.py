import hashlib
import json
from django.db import models
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder

class FactDefinition(models.Model):
    """
    Represents what a fact is (stable identity).
    """
    class FactValueType(models.TextChoices):
        SCALAR = 'scalar', 'Scalar'
        DICT = 'dict', 'Dict'
        LIST = 'list', 'List'
        DATAFRAME = 'dataframe', 'Dataframe'
        DISTRIBUTION = 'distribution', 'Distribution'

    id = models.CharField(max_length=255, primary_key=True) # snake_case, stable
    description = models.TextField(blank=True)
    data_type = models.CharField(
        max_length=50, 
        choices=FactValueType.choices, 
        default=FactValueType.SCALAR
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.id

class FactDefinitionVersion(models.Model):
    """
    Represents how the fact is computed (versioned logic).
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('deprecated', 'Deprecated'),
    ]
    
    fact_definition = models.ForeignKey(FactDefinition, on_delete=models.CASCADE, related_name='versions')
    version = models.IntegerField()
    requires = models.JSONField(default=list) # list of fact ids
    parameters_schema = models.JSONField(default=dict, blank=True)
    output_template = models.TextField(blank=True, null=True)
    code = models.TextField(help_text="Python code or DSL")
    test_cases = models.JSONField(default=list, blank=True, help_text="List of {context, expected} for validation")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    change_note = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('fact_definition', 'version')
        ordering = ['-version']

    def __str__(self):
        return f"{self.fact_definition_id} v{self.version}"

class FactInstance(models.Model):
    """
    Reusable cached computation.
    """
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
    ]
    
    fact_version = models.ForeignKey(FactDefinitionVersion, on_delete=models.CASCADE, related_name='instances')
    context = models.JSONField(default=dict, encoder=DjangoJSONEncoder)
    context_hash = models.CharField(max_length=64, db_index=True)
    value = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    computed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success')
    error = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['fact_version', 'context_hash']),
        ]
        unique_together = ('fact_version', 'context_hash')
    
    def __str__(self):
        return f"{self.fact_version} ({self.status})"

class FactInstanceDependency(models.Model):
    parent_instance = models.ForeignKey(FactInstance, on_delete=models.CASCADE, related_name='dependencies')
    dependency_instance = models.ForeignKey(FactInstance, on_delete=models.CASCADE, related_name='dependents')
    dependency_fact_id = models.CharField(max_length=255)

class Question(models.Model):
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return self.text

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.TextField()
    facts_used = models.ManyToManyField(FactInstance, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer to: {self.question.text[:50]}..."
