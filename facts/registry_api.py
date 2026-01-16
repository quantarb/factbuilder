from django.db.models import Q
from facts.models import FactDefinition, FactDefinitionVersion, IntentRecognizer

def list_facts(namespace: str = None):
    """
    Lists facts, optionally filtered by namespace.
    """
    qs = FactDefinition.objects.filter(is_active=True)
    if namespace:
        qs = qs.filter(namespace=namespace)
    return list(qs.values('id', 'description', 'namespace', 'slug'))

def search_facts(query: str):
    """
    Searches facts by keyword over name, description, and recognizer examples.
    """
    # 1. Search definitions
    def_matches = FactDefinition.objects.filter(
        Q(id__icontains=query) | 
        Q(description__icontains=query)
    ).values_list('id', flat=True)
    
    # 2. Search recognizers
    rec_matches = IntentRecognizer.objects.filter(
        Q(example_questions__icontains=query) |
        Q(keywords__icontains=query)
    ).values_list('fact_version__fact_definition__id', flat=True)
    
    # Combine results
    all_ids = set(def_matches) | set(rec_matches)
    
    return FactDefinition.objects.filter(id__in=all_ids).values('id', 'description', 'namespace')
