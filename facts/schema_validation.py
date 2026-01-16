import jsonschema
from jsonschema import validate, ValidationError
from typing import Any, Dict, Optional

def validate_schema_definition(schema: Dict[str, Any]) -> None:
    """
    Validates that the provided schema is a valid JSON Schema.
    """
    try:
        jsonschema.Draft7Validator.check_schema(schema)
    except jsonschema.exceptions.SchemaError as e:
        raise ValueError(f"Invalid JSON Schema: {e.message}")

def validate_context(context: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """
    Validates the runtime context against the provided JSON Schema.
    """
    if not schema:
        return

    try:
        validate(instance=context, schema=schema)
    except ValidationError as e:
        raise ValueError(f"Context validation failed: {e.message}")
