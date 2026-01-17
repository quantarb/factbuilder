import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from django.db import models
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from simple_history.models import HistoricalRecords

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
    namespace = models.CharField(max_length=100, blank=True, db_index=True)
    slug = models.CharField(max_length=100, blank=True, db_index=True)
    description = models.TextField(blank=True)
    data_type = models.CharField(
        max_length=50, 
        choices=FactValueType.choices, 
        default=FactValueType.SCALAR
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.namespace or not self.slug:
            # Auto-populate from id if missing
            parts = self.id.split('.', 1)
            if len(parts) == 2:
                self.namespace, self.slug = parts
            else:
                self.namespace = 'default'
                self.slug = self.id
        super().save(*args, **kwargs)

    def __str__(self) -> str:
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
    
    LOGIC_TYPE_CHOICES = [
        ('python', 'Python'),
        ('expression', 'Expression (SimpleEval)'),
    ]
    
    fact_definition = models.ForeignKey(FactDefinition, on_delete=models.CASCADE, related_name='versions')
    version = models.IntegerField()
    requires = models.JSONField(default=list) # list of fact ids (Legacy)
    dependencies = models.JSONField(default=list, blank=True, help_text="Structured dependency edges")
    parameters_schema = models.JSONField(default=dict, blank=True)
    output_template = models.TextField(blank=True, null=True)
    logic_type = models.CharField(max_length=20, choices=LOGIC_TYPE_CHOICES, default='python')
    code = models.TextField(help_text="Python code or DSL")
    test_cases = models.JSONField(default=list, blank=True, help_text="List of {context, expected} for validation")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    change_note = models.TextField(blank=True)
    history = HistoricalRecords()
    
    class Meta:
        unique_together = ('fact_definition', 'version')
        ordering = ['-version']

    def __str__(self) -> str:
        return f"{self.fact_definition_id} v{self.version}"

class IntentRecognizer(models.Model):
    """
    Stores recognition data for a specific fact version.
    """
    fact_version = models.OneToOneField(FactDefinitionVersion, on_delete=models.CASCADE, related_name='recognizer')
    example_questions = models.JSONField(default=list, blank=True)
    regex_patterns = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Recognizer for {self.fact_version}"

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
    
    # Provenance fields
    provenance = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    confidence = models.FloatField(default=1.0)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    computed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success')
    error = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['fact_version', 'context_hash']),
        ]
        unique_together = ('fact_version', 'context_hash')
    
    def __str__(self) -> str:
        return f"{self.fact_version} ({self.status})"

class FactInstanceDependency(models.Model):
    parent_instance = models.ForeignKey(FactInstance, on_delete=models.CASCADE, related_name='dependencies')
    dependency_instance = models.ForeignKey(FactInstance, on_delete=models.CASCADE, related_name='dependents')
    dependency_fact_id = models.CharField(max_length=255)

class Question(models.Model):
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self) -> str:
        return self.text

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.TextField()
    facts_used = models.ManyToManyField(FactInstance, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Answer to: {self.question.text[:50]}..."
