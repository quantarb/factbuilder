# FactBuilder Project Description

FactBuilder is a Django-based financial intelligence application that allows users to query their financial data using natural language. It ingests bank and credit card transactions and uses a flexible "Fact Taxonomy" system to compute insights dynamically.

## Core Functionality

*   **Data Ingestion**: Imports transaction history from CSV files into a structured relational database.
*   **Natural Language QA**: Users can ask questions like "How much did I spend on 2026-01-02?" or "What is my current balance?".
*   **Fact Taxonomy**: A dependency-based engine that defines how to compute various financial facts (e.g., calculating "spending by category" requires "all transactions").
*   **Interaction History**: Logs all user questions, the system's answers, and the specific facts computed during the session.

## Architecture

The system is built on a modular architecture separating data storage, logic computation, and user interaction.

```mermaid
graph TD
    User[User] -->|Asks Question| QA[QA Engine]
    
    subgraph "Facts Module"
        QA -->|Parse Intent| Intent[Intent Recognition]
        QA -->|Request Fact| Registry[Fact Registry / Taxonomy]
        Registry -->|Resolve Dependencies| Producer[Fact Producers]
        Producer -->|Compute| ComputedVal[Computed Value]
        QA -->|Save Interaction| History[History Store (Question/Answer/Fact)]
    end
    
    subgraph "Finance Module"
        Producer -->|Query Data| Models[Finance Models]
        Models -->|Read| DB[(Database)]
    end

    ComputedVal -->|Return| QA
    QA -->|Format Answer| User
```

## Component Breakdown

### 1. Finance Module (`finance`)
Responsible for the raw data layer.
*   **Models**: `Account`, `BankTransaction`, `CreditCardTransaction`.
*   **Data Source**: CSV files (`bank_transactions.CSV`, `creditcard_transactions.CSV`) ingested via `python manage.py setup_data`.

### 2. Facts Module (`facts`)
The brain of the application, split into definition, execution, and storage.

*   **Taxonomy (`taxonomy.py`)**:
    *   Defines `FactSpec` objects (metadata about a fact).
    *   Manages a dependency graph (e.g., `current_balance` depends on raw DB queries; `spending_by_category` depends on `all_transactions`).
    *   **Producers**: Python functions that execute the logic to compute values from the database.

*   **QA Engine (`engine.py`)**:
    *   **Intent Recognition**: Maps text patterns (Regex) to Fact IDs.
    *   **Context Extraction**: Pulls entities like Dates or Account Names from the question.
    *   **Orchestration**: Calls the Taxonomy to resolve facts and formats the output into human-readable text.

*   **Storage (`models.py`)**:
    *   `FactType`: Registry of available fact definitions in the DB.
    *   `Fact`: Stored instances of computed values with their context (JSON).
    *   `Question` & `Answer`: Audit trail of user interactions.

### 3. Web Interface
*   **Django Views**: Handles HTTP requests to interact with the QA Engine (currently structured within the `conversations` and `facts` apps).
