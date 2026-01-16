from django.db import models
from django.contrib.auth.models import User
from facts.models import Question, Answer
from agents.models import TaxonomyProposal

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title or 'Conversation'} ({self.created_at.strftime('%Y-%m-%d')})"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=[('user', 'User'), ('bot', 'Bot')])
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional: Link to the underlying Question/Answer objects from the facts app
    related_question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, blank=True)
    related_answer = models.ForeignKey(Answer, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Link to a proposal if this message is presenting one
    related_proposal = models.ForeignKey(TaxonomyProposal, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender}: {self.text[:50]}..."
