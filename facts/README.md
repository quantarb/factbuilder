# Facts App

The `facts` app is the core engine of the FactBuilder project. It is responsible for defining, versioning, and executing "facts" — units of logic that compute values based on context and dependencies.

## Main Interfaces

### Models

*   **`FactDefinition`**: Represents the stable identity of a fact (e.g., `finance.monthly_spending`). It defines the data type (scalar, list, dict, etc.) and basic metadata.
*   **`FactDefinitionVersion`**: Contains the actual logic for a fact. Facts are versioned, allowing for evolution of logic over time. It supports Python code or simple expressions.
*   **`FactInstance`**: A cached computation result for a specific fact version and context. It ensures that expensive computations are reused.
*   **`IntentRecognizer`**: Maps natural language questions to specific fact versions using regex, keywords, or examples.

### Core Logic

*   **`engine.py`**: Likely contains the execution engine that resolves dependencies and runs the logic defined in `FactDefinitionVersion`.
*   **`executor.py`**: Handles the execution of the code or expressions.
*   **`taxonomy.py`**: Manages the hierarchy and organization of facts.
*   **`registry_api.py`**: Provides an API for registering and retrieving facts.

## Contract

*   **Fact Execution**: Facts take a `context` (JSON) and `dependencies` (other facts) as input and produce a value.
*   **Versioning**: Changes to logic should create a new `FactDefinitionVersion`.
*   **Caching**: Results are cached in `FactInstance` based on a hash of the context.
