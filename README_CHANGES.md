# Changes Summary

## 1. Data Type Enum
We introduced `FactDefinition.FactValueType` (scalar, dict, list, dataframe, distribution) to enforce consistent data types across the system.
- Updated `FactDefinition` model.
- Updated `TaxonomyProposal` to validate against this enum.

## 2. Caching & Concurrency
- Added `unique_together = ('fact_version', 'context_hash')` to `FactInstance` to prevent duplicates.
- Updated `resolve_fact` to use `transaction.atomic()` and `get_or_create` for thread-safe caching.
- Implemented recursive, stable context normalization (`normalize_context`) and hashing (`hash_context`).

## 3. Safe Execution
- Implemented `safe_execute` which runs dynamic fact code in a separate `multiprocessing.Process`.
- Enforced a timeout (default 5s).
- Restricted globals (no `import`, limited builtins).
- Note: `all_transactions` still accesses DB models, which is allowed but requires care in multiprocessing.

## 4. All Transactions Seed
- Removed hardcoded `all_transactions` from `build_taxonomy`.
- Added `seed_all_transactions` management command to populate it as a normal DB fact.

## 5. Taxonomy Proposal Workflow
- Enhanced `TaxonomyProposal` with structured fields (`proposed_data_type`, `proposed_requires`, `test_cases`).
- Added validation logic in `approve()`: checks requirements, data type, and runs test cases using `safe_execute`.

## How to Test
1. Run migrations: `python manage.py makemigrations facts agents && python manage.py migrate`
2. Seed data: `python manage.py seed_all_transactions`
3. Run tests: `python manage.py test facts.tests`
