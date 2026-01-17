import re
from typing import Optional, Dict, Any, List, Tuple
from facts.models import FactDefinitionVersion, IntentRecognizer
from facts.context import normalize_context

try:
    from rapidfuzz import fuzz, process
except ImportError:
    fuzz = None
    process = None

class IntentRouter:
    """
    Routes user questions to the appropriate fact definition version based on intent recognition.
    """
    def __init__(self) -> None:
        self._regex_cache = {}
        self._keyword_cache = {}
        self._load_recognizers()

    def _load_recognizers(self) -> None:
        """
        Loads all active recognizers into memory.
        In a production app, this should be cached and invalidated on updates.
        """
        self.recognizers = []
        # Only consider approved versions
        versions = FactDefinitionVersion.objects.filter(status='approved').select_related('fact_definition', 'recognizer')
        
        for v in versions:
            if hasattr(v, 'recognizer'):
                rec = v.recognizer
                self.recognizers.append({
                    'version': v,
                    'regex': [re.compile(p, re.IGNORECASE) for p in rec.regex_patterns],
                    'keywords': rec.keywords,
                    'examples': rec.example_questions
                })

    def route(self, text: str) -> Tuple[Optional[FactDefinitionVersion], Dict[str, Any]]:
        """
        Routes a question to a FactDefinitionVersion and extracts parameters.
        """
        # 1. Regex Match (Highest Priority)
        for item in self.recognizers:
            for pattern in item['regex']:
                match = pattern.search(text)
                if match:
                    # Extract named groups as context
                    context = match.groupdict()
                    return item['version'], context

        # 2. Keyword/Fuzzy Match
        best_score = 0
        best_version = None
        
        for item in self.recognizers:
            score = 0
            
            # A. Fuzzy match against examples (if available)
            if fuzz and item['examples']:
                match = process.extractOne(text, item['examples'], scorer=fuzz.token_sort_ratio)
                if match:
                    fuzzy_score = match[1]
                    if fuzzy_score > score:
                        score = fuzzy_score
            
            # B. Keyword scoring (fallback or boost)
            if item['keywords']:
                # Simple keyword overlap score
                # We normalize to 0-100 scale roughly
                keywords_found = sum(1 for k in item['keywords'] if k.lower() in text.lower())
                if len(item['keywords']) > 0:
                    keyword_score = (keywords_found / len(item['keywords'])) * 90
                    if keyword_score > score:
                        score = keyword_score
            
            if score > best_score and score > 60: # Threshold
                best_score = score
                best_version = item['version']

        if best_version:
            return best_version, {}

        return None, {}

    def refresh(self) -> None:
        """
        Reloads recognizers from the database.
        """
        self._load_recognizers()
