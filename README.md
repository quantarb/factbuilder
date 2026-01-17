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

### Level 0 — Trust & Ground Truth (Point-in-Time)
“What is true right now, and why?”

These questions establish verifiable ground truth.
* What is my current cash balance?
* Where did this number come from?

**Characteristics:**
* Deterministic
* Fully explainable
* No inference
* No parameters (implicit “now” only)

If the system cannot fully explain the answer, it must refuse to answer.

### Level 1 — Parameterized Ground Truth (Transactions + Filters)
“What was true when, where, or for which slice?”

Level 1 introduces parameters, not new concepts. These questions are answered directly from transactions using:
* Time ranges
* Filters
* Simple aggregations

**Examples:**
* **Time-based:**
    * How much did I spend yesterday?
    * How much did I spend last week?
    * What was my balance on January 1st?
* **Filter-based:**
    * How much did I spend on groceries last month?
    * How much did I spend at Amazon in the last 90 days?
    * How much income did I receive in the past 2 months?
* **Combined:**
    * How much did I spend on restaurants in the last 2 months?
    * What were my largest expenses last week?

**What Level 1 does not assume:**
* No bills
* No paychecks
* No obligations
* No recurring patterns
* No prediction

If the system only knows transactions, Level 1 is still fully answerable.

### Level 2 — Inferred Structure (Patterns from Transactions)
“What appears to be true repeatedly?”

Level 2 introduces inference. Here, the system begins proposing structure that is not explicitly stated in transactions.

**Examples:**
* What recurring bills do I appear to have based on my transactions?
* What recurring income do I appear to have based on my transactions?
* How confident are you in these recurring patterns?

**Key properties:**
* Answers include confidence
* Supporting evidence is required
* Results are hypotheses, not ground truth

**Failure mode:**
If patterns are weak or ambiguous, the system must say so.

### Level 3 — Available-to-Spend (MVP Boundary)
“Given what’s known and inferred, what is safe to spend?”

**Examples:**
* How much money is actually available to spend right now?
* How confident are you in that number?

This level combines:
* Ground truth (Levels 0–1)
* Inferred structure (Level 2)

Uncertainty must be explicit. If uncertainty is too high, the system should decline to give a definitive number.

### Level 4 — Spending Context
“How does my current behavior compare to my past?”

**Examples:**
* How much have I spent so far this month?
* Is that more or less than usual for this point in the month?
* What category is driving the difference?

These questions require:
* Historical baselines
* Meaningful comparisons
* Attribution

### Level 5 — Counterfactuals
“What if I make a different choice?”

**Examples:**
* What happens if I don’t spend anything else this month?
* What happens if I spend $X today?
* What changes if I wait a week?

Outputs are scenarios, not predictions.

### Level 6 — Risk & Regret
“What could go wrong, and where is uncertainty concentrated?”

**Examples:**
* Does spending $X increase my financial risk?
* What uncertainty is this decision sensitive to?
* What am I most likely to regret about this purchase?

Risk is probabilistic and contextual.

### Level 7 — Frugal Mode Decision
“Given everything you know and don’t know, what should I do?”

**Examples:**
* Can I afford to spend $X right now without increasing my financial risk?
* Should I do this now, wait, or not do it — and how confident are you?

If earlier levels are incomplete, the system must refuse to recommend.

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
