from django.test import TestCase
from facts.schema_validation import validate_schema_definition, validate_context

class SchemaValidationTests(TestCase):
    """
    Tests for JSON schema validation of context and schema definitions.
    """
    def test_validate_schema_definition(self) -> None:
        """
        Test that valid and invalid schema definitions are correctly identified.
        """
        valid_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        }
        validate_schema_definition(valid_schema)
        
        invalid_schema = {"type": "unknown_type"}
        with self.assertRaises(ValueError):
            validate_schema_definition(invalid_schema)

    def test_validate_context(self) -> None:
        """
        Test that context data is validated against a schema.
        """
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "minimum": 0}
            },
            "required": ["age"]
        }
        
        validate_context({"age": 25}, schema)
        
        with self.assertRaises(ValueError):
            validate_context({"age": -5}, schema)
            
        with self.assertRaises(ValueError):
            validate_context({}, schema)
