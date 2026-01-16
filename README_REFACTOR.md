# FactBuilder Refactoring

This document outlines the changes made to refactor FactBuilder to leverage popular packages and improve robustness.

## Changes

### 1. Dependencies
Added the following packages to `requirements.txt`:
- `pydantic`: For context validation and normalization.
- `jsonschema`: For validating fact parameter schemas.
- `networkx`: For dependency graph construction and cycle detection.
- `django-simple-history`: For model versioning and audit trails.
- `simpleeval`: For safe execution of user-defined logic expressions.
- `django-redis`: (Optional) For caching.

### 2. Configuration
- Configured `django-simple-history` in `settings.py`.
- Added `simple_history` to `INSTALLED_APPS` and `MIDDLEWARE`.

### 3. Context Management (`facts/context.py`)
- Implemented `normalize_context` to ensure consistent hashing of contexts (handling dates, decimals, and nested structures).
- Implemented `hash_context` for stable cache keys.

### 4. Schema Validation (`facts/schema_validation.py`)
- Added validation for `parameters_schema` using `jsonschema`.
- Runtime contexts are now validated against the schema before fact resolution.

### 5. Dependency Graph (`facts/graph.py`)
- Uses `networkx` to build a dependency graph of facts.
- Detects cycles during taxonomy build time to prevent infinite recursions.

### 6. Safe Execution (`facts/executor.py`)
- Integrated `simpleeval` for safe execution of logic expressions.
- Added `logic_type` to `FactDefinitionVersion` to support 'python' (legacy/advanced) and 'expression' (safe/simple) logic.

### 7. Taxonomy Proposals (`agents/models.py`)
- Enhanced `TaxonomyProposal` to include schema, template, and logic type.
- `approve()` method now validates schemas, data types, and runs test cases before creating a new version.

### 8. Concurrency & Caching (`facts/taxonomy.py`)
- Refactored `resolve_fact` to use `transaction.atomic` and `get_or_create` to handle race conditions when creating `FactInstance`.
- Integrated cycle detection and schema validation into the resolution flow.

## How to Run Locally

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Apply Migrations:**
   Since model changes were made (adding history, new fields), you need to create and apply migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Run Tests:**
   Verify the changes with the new tests:
   ```bash
   python manage.py test facts.tests
   ```

4. **Run Server:**
   ```bash
   python manage.py runserver
   ```

## New Features Usage

- **Defining a Fact with Expression:**
  When creating a `FactDefinitionVersion`, set `logic_type='expression'` and provide a simple Python expression in `code`.
  Example: `sum([t['amount'] for t in transactions])`

- **Schema Validation:**
  Provide a JSON Schema in `parameters_schema`. The system will automatically validate the context against this schema.

- **Cycle Detection:**
  The system will raise a `ValueError` on startup (or when building taxonomy) if a dependency cycle is detected.
