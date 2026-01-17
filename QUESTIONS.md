# The Frugal Knowledge Ladder

This document outlines the hierarchy of questions FactBuilder is designed to answer, moving from raw data to high-stakes decision support.

## Level 0: Ground Truth (The "What")
**Goal:** Accurate reporting of current state and history.
**Enabling App:** `finance`
**Models:** `FinancialAccount`, `Transaction`

*   "What is my current checking account balance?"
*   "How much did I spend at Starbucks last month?"
*   "Show me all transactions from yesterday."
*   "What is the total balance across all my credit cards?"

## Level 1: Parameterized Truth (The "What if I slice it?")
**Goal:** Flexible aggregation and filtering of ground truth.
**Enabling App:** `facts` (Engine) + `finance`

*   "How much did I spend on 'Dining Out' in 2023?"
*   "What was my average weekly spending in November?"
*   "Which merchant did I visit most frequently last year?"

## Level 2: Inferred Structure (The "What is recurring?")
**Goal:** Distinguishing one-offs from structural commitments.
**Enabling App:** `frugal`
**Models:** `RecurrenceCandidate`, `RecurringExpense`, `Entity`

*   "What are my monthly fixed costs?"
*   "Do I have any subscriptions I forgot about?"
*   "How much of my income is automatically spoken for before I wake up?"
*   "Is this $50 charge a one-time event or a new monthly bill?"

## Level 3: Available-to-Spend (The "What is truly mine?")
**Goal:** Calculating "Safe-to-Spend" (Free Cash Flow) by subtracting commitments from liquidity.
**Enabling App:** `frugal`
**Models:** `ReservePolicy`, `ReserveInstance`, `RecurringExpense`

*   "I have $5,000 in the bank, but how much can I actually spend today without hurting my future self?"
*   "Am I on track to fund my Emergency Fund this month?"
*   "If I pay all my bills due before next payday, what is left?"

## Level 4: Context (The "Is this normal?")
**Goal:** Benchmarking against self and goals.
**Enabling App:** `frugal` + `facts`

*   "Is my grocery spending trending up or down?"
*   "How does this month's spending compare to my 6-month average?"
*   "Why is my 'Safe-to-Spend' number lower than usual?"

## Level 5: Counterfactuals (The "What if?")
**Goal:** Simulating future scenarios based on structural knowledge.
**Enabling App:** `frugal` (Simulation)

*   "If I cancel Netflix and Spotify, how much will I save in a year?"
*   "If I buy this $2,000 laptop today, will I be able to pay rent next month?"
*   "What happens to my savings rate if my rent increases by $100?"

## Level 6: Risk & Regret (The "Should I?")
**Goal:** Emotional and risk-based assessment.
**Enabling App:** `agents` (LLM analysis of `frugal` data)

*   "Can I afford this vacation without dipping into my emergency fund?"
*   "How risky is my current burn rate given my income stability?"
*   "If I buy this car, how many months of freedom am I trading for it?"

## Level 7: Frugal Decision (The "Action")
**Goal:** Definitive guidance on resource allocation.

*   "Transfer $500 to savings now."
*   "Reject this purchase."
*   "Switch to a cheaper plan."
