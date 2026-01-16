from django.core.management.base import BaseCommand
from agents.llm_service import LLMService
from agents.models import CapabilitySuggestion

class Command(BaseCommand):
    help = 'Asks the LLM to suggest new capabilities (questions) the system could answer.'

    def handle(self, *args, **options):
        self.stdout.write("Asking LLM for capability suggestions...")
        
        service = LLMService()
        # In a real app, we would pass the actual current taxonomy description here
        suggestions = service.suggest_capabilities("Current capabilities: Balance, Spending by Category, Spending on Date")
        
        count = 0
        for s in suggestions:
            # Avoid duplicates
            if not CapabilitySuggestion.objects.filter(suggested_question=s['question']).exists():
                CapabilitySuggestion.objects.create(
                    suggested_question=s['question'],
                    reasoning=s['reasoning']
                )
                count += 1
                self.stdout.write(f"Added suggestion: {s['question']}")
            else:
                self.stdout.write(f"Skipped duplicate: {s['question']}")
                
        self.stdout.write(self.style.SUCCESS(f"Successfully added {count} new suggestions."))
