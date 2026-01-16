from django.db import models
from django.contrib.auth.models import User

class FactType(models.Model):
    """
    Defines a category of facts (e.g., 'Current Balance', 'Daily Spending').
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    data_type = models.CharField(max_length=50, default='string')
    required_context = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return self.name

class DynamicFact(models.Model):
    """
    Stores dynamically generated fact definitions and their executable code.
    """
    id = models.CharField(max_length=255, primary_key=True)
    description = models.TextField()
    kind = models.CharField(max_length=50, default="computed")
    data_type = models.CharField(max_length=50, default="scalar")
    requires = models.JSONField(default=list)
    
    # The Python code for the producer function
    code = models.TextField(help_text="Python code defining the producer function.")
    
    # NEW: JSON Schema defining what context variables this fact accepts/uses
    # e.g. {"type": "object", "properties": {"date": {"type": "string"}}, "required": ["date"]}
    parameters_schema = models.JSONField(default=dict, blank=True, help_text="JSON Schema for context parameters")
    
    # NEW: Template for formatting the answer
    # e.g. "You spent ${value} on {date}."
    output_template = models.TextField(blank=True, null=True, help_text="Jinja2-style template for the answer string")

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.id

class Fact(models.Model):
    fact_type = models.ForeignKey(FactType, on_delete=models.CASCADE)
    context = models.JSONField(default=dict, blank=True)
    value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['fact_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.fact_type.name} {self.context}: {self.value}"

class Question(models.Model):
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return self.text

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.TextField()
    facts_used = models.ManyToManyField(Fact, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer to: {self.question.text[:50]}..."
