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

See [QUESTIONS.md](QUESTIONS.md) for the detailed hierarchy.

### Level 0 — Trust & Ground Truth (Point-in-Time)
“What is true right now, and why?”

### Level 1 — Parameterized Ground Truth (Transactions + Filters)
“What was true when, where, or for which slice?”

### Level 2 — Inferred Structure (Patterns from Transactions)
“What appears to be true repeatedly?”

### Level 3 — Available-to-Spend (MVP Boundary)
“Given what’s known and inferred, what is safe to spend?”

### Level 4 — Spending Context
“How does my current behavior compare to my past?”

### Level 5 — Counterfactuals
“What if I make a different choice?”

### Level 6 — Risk & Regret
“What could go wrong, and where is uncertainty concentrated?”

### Level 7 — Frugal Decision
“Given everything you know and don’t know, what should I do?”

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

### 2. Fact Taxonomy Engine
The Fact Taxonomy is the deterministic reasoning layer.
Facts are explicit, versioned computations. Each fact declares:
* dependencies
* parameters
* outputs

Facts form a directed acyclic dependency graph. Examples:
* `money.reserved` → depends on upcoming bills
* `money.available` → depends on balances and reserves
* `risk.delta($X)` → depends on available-to-spend and obligations

The taxonomy ensures that complex questions can be answered by composing simpler, defensible facts.

### 3. Frugal Inference & Decision Layer
The `frugal` app manages the transition from raw data to structural knowledge.
* **Inference**: Detects recurring patterns (`RecurrenceCandidate`) from transactions.
* **Confirmation**: Users validate candidates to create confirmed facts (`RecurringExpense`).
* **Policy**: Defines "Available-to-Spend" logic via `ReservePolicy`.

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
