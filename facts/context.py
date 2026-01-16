import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Union

from pydantic import BaseModel, Field

class BaseContextModel(BaseModel):
    """
    Base model for context validation.
    Accepts arbitrary nested JSON.
    """
    class Config:
        extra = "allow"
        arbitrary_types_allowed = True

def normalize_context(context: Any) -> Any:
    """
    Normalize context for hashing recursively:
    - Sort keys
    - Remove transient keys (user, request, session_id)
    - Convert dates to ISO strings
    - Normalize Decimal to float (or string, but float is more common for JSON)
    - Normalize lists/tuples
    """
    if isinstance(context, dict):
        clean_ctx = {}
        for k, v in context.items():
            if k in ['user', 'request', 'session_id']:
                continue
            clean_ctx[k] = normalize_context(v)
        return clean_ctx
    elif isinstance(context, (list, tuple)):
        return [normalize_context(x) for x in context]
    elif isinstance(context, (date, datetime)):
        return context.isoformat()
    elif isinstance(context, Decimal):
        return float(context)
    elif isinstance(context, float):
        return float(context)
    else:
        return context

def hash_context(context: Dict[str, Any]) -> str:
    """SHA256 hash of normalized context."""
    norm = normalize_context(context)
    # Ensure consistent ordering with sort_keys=True
    s = json.dumps(norm, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(s.encode('utf-8')).hexdigest()
