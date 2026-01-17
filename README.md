# FactBuilder — A Frugal Mode Financial Intelligence System

## Project Overview

FactBuilder is a system for answering progressively harder personal finance questions, starting from raw transactions and building upward toward high-stakes, uncertainty-aware spending decisions.

The system is intentionally layered. Each level introduces new kinds of knowledge derived from the previous ones.

If a question cannot be answered with the knowledge available at a given level, FactBuilder should say so explicitly.

> “This question cannot be answered yet with sufficient confidence.”

That restraint is a core feature of the system.

## Starting Point: Transactions First

FactBuilder begins with transactions.

Transactions are the only assumed primitive at the start:
* Money moving in or out
* Amounts
* Dates
* Descriptions
* Optional categories or metadata

Everything else — balances, spending summaries, obligations, income, risk, regret — is derived from transactions over time.

No higher-level concept is assumed until the system has enough evidence to justify it.

## Design Principles

* **Epistemic honesty**: Facts are only asserted when they can be justified from prior knowledge.
* **Levels are knowledge boundaries**: Higher levels depend on lower levels being correct and complete.
* **Inference increases uncertainty**: As questions move up levels, answers may include confidence, caveats, or refusal.
* **“Not answerable yet” is a valid answer**: The system must not guess its way past missing knowledge.

## The Question Ladder (North Star)

The core philosophy of FactBuilder is the **Question Ladder**, which defines the hierarchy of financial intelligence.

👉 **[See QUESTIONS.md for the detailed hierarchy and example questions.](QUESTIONS.md)**

*   **Level 0**: Ground Truth (The "What")
*   **Level 1**: Parameterized Truth (The "What if I slice it?")
*   **Level 2**: Inferred Structure (The "What is recurring?")
*   **Level 3**: Available-to-Spend (The "What is truly mine?")
*   **Level 4**: Context (The "Is this normal?")
*   **Level 5**: Counterfactuals (The "What if?")
*   **Level 6**: Risk & Regret (The "Should I?")
*   **Level 7**: Frugal Decision (The "Action")

## Core Functionality

### 1. Data Ingestion
FactBuilder ingests raw financial data as ground-truth inputs, not insights.
* Bank transactions
* Credit card transactions
* Accounts and balances
* Bills and known obligations

Data is imported from CSV files into a relational database via:
```bash
python manage.py setup_data
```

👉 **See [finance/README.md](finance/README.md) for details on the data models.**

### 2. Fact Taxonomy Engine
The Fact Taxonomy is the deterministic reasoning layer.
Facts are explicit, versioned computations. Each fact declares:
* dependencies
* parameters
* outputs

Facts form a directed acyclic dependency graph. The taxonomy ensures that complex questions can be answered by composing simpler, defensible facts.

👉 **See [facts/README.md](facts/README.md) for details on the engine and taxonomy.**

### 3. Frugal Inference & Decision Layer
The `frugal` app manages the transition from raw data to structural knowledge.
* **Inference**: Detects recurring patterns (`RecurrenceCandidate`) from transactions.
* **Confirmation**: Users validate candidates to create confirmed facts (`RecurringExpense`).
* **Policy**: Defines "Available-to-Spend" logic via `ReservePolicy`.

👉 **See [frugal/README.md](frugal/README.md) for details on inference and decision models.**

### 4. LLM-Assisted Coding Agent (Capacity Builder)
FactBuilder includes an LLM-assisted coding agent whose sole responsibility is to expand the fact taxonomy, not to answer user questions directly.

The agent is used to:
* Propose new fact definitions
* Generate candidate computation logic
* Suggest dependency graphs
* Create test cases and validation data
* Refactor or generalize existing facts

All LLM-generated proposals:
* are stored as drafts
* require validation and approval
* become deterministic, versioned facts once accepted

This allows FactBuilder to grow its reasoning capacity safely over time, without embedding opaque LLM reasoning into runtime decisions.

### 5. Natural Language Question Answering
Users interact with FactBuilder using natural language, but natural language serves only as a routing and parameter-extraction layer.

The QA Engine:
* Maps questions to the appropriate level in the question ladder
* Identifies the required facts
* Resolves dependencies through the taxonomy
* Returns answers with:
    * computed values
    * provenance
    * confidence
    * explicit assumptions

### 6. Interaction History & Auditability
Every question is fully auditable.
For each interaction, FactBuilder records:
* the user’s question
* the system’s answer
* the facts computed
* dependencies used
* confidence and assumptions

This audit trail is critical for trust, debugging, and iterative improvement.

## Architecture Overview

```mermaid
graph TD
    User --> QA_Engine[QA Engine]
    QA_Engine --> Fact_Registry[Fact Registry / Taxonomy]
    Fact_Registry --> Fact_Producers[Fact Producers (Deterministic Computation)]
    Fact_Producers --> Finance_Models[Finance Models (Level 0/1)]
    Fact_Producers --> Frugal_Models[Frugal Models (Level 2+)]
    
    LLM_Agent[LLM-Assisted Coding Agent] -->|Proposes / Extends Facts| Fact_Registry
```

* Runtime answers never depend on live LLM reasoning
* All decisions are traceable to stored facts
