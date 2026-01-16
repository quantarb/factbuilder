# FactBuilder — A Frugal Mode Financial Intelligence System

## Project Overview

FactBuilder is a Django-based financial intelligence application designed to answer a progressive sequence of financial questions, culminating in one core decision:

> “Given everything I know and don’t know, should I spend $X right now — or wait — without increasing my financial risk?”

FactBuilder is built around a fact-based taxonomy and an LLM-assisted coding agent that helps build, extend, and evolve the system’s reasoning capabilities over time.

Rather than relying on an LLM to answer financial questions directly, FactBuilder uses LLMs to author, propose, and refine new facts and computations—which are then executed deterministically by the system.

## The Question Ladder (North Star)

FactBuilder exists to support the following 20 questions, ordered from basic ground truth to high-stakes frugal decisions:

### Level 0 — Trust & Ground Truth
* What is my current cash balance?
* Where did this number come from?

### Level 1 — Time & Obligations
* What was my balance yesterday?
* What bills are due before my next paycheck?
* How much money is already spoken for?

### Level 2 — Available-to-Spend (MVP Boundary)
* How much money is actually available to spend right now?
* How confident are you in that number?

### Level 3 — Spending Context
* How much have I spent so far this month?
* Is that more or less than usual for this point in the month?
* What category is driving the difference?

### Level 4 — Counterfactuals
* What happens if I don’t spend anything else this month?
* What happens if I spend $X today?
* What changes if I wait a week?

### Level 5 — Risk & Regret
* Does spending $X increase my financial risk?
* What uncertainty is this decision sensitive to?
* What am I most likely to regret about this purchase?

### Level 6 — Tradeoffs
* If I make this purchase, what will I likely have to give up later?
* If I need to save $X later, what should I cut first?

### Level 7 — Frugal Mode Decision
* Can I afford to spend $X right now without increasing my financial risk?
* Given everything you know and don’t know, should I do this now, wait, or not do it — and how confident are you?

## Core Philosophy

* Facts over heuristics
* Provenance over precision
* Confidence is required, not optional
* “Do nothing” is a valid recommendation
* LLMs build capabilities; they do not decide outcomes
* The system may refuse to answer if required facts or confidence thresholds are not met.

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

### 3. LLM-Assisted Coding Agent (Capacity Builder)
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

### 4. Natural Language Question Answering
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

### 5. Interaction History & Auditability
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
    Fact_Producers --> Finance_Models[Finance Models / Database]
    
    LLM_Agent[LLM-Assisted Coding Agent] -->|Proposes / Extends Facts| Fact_Registry
```

* Runtime answers never depend on live LLM reasoning
* All decisions are traceable to stored facts
