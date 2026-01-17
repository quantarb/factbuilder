# Frugal App (Level 2+)

The `frugal` app manages the **Inferred Structure** and **Decision Logic** of the system. It bridges the gap between raw transactions and actionable advice.

## Role in Knowledge Ladder

*   **Level 2 (Inferred Structure)**: Detects and confirms recurring patterns (Bills, Income).
*   **Level 3 (Available-to-Spend)**: Defines policies for reserves and safe spending limits.
*   **Level 4+ (Context & Decisions)**: Provides the structural basis for counterfactuals and risk assessment.

## Main Interfaces

### Models

#### Entity Abstraction
*   **`Entity`**: A canonical merchant or payer (e.g., "Netflix", "Employer").
*   **`EntityAlias`**: Maps raw transaction descriptions (e.g., "NETFLIX.COM* CA") to an Entity.

#### Inference Workflow
*   **`RecurrenceCandidate`**: A system-generated hypothesis about a recurring expense or income. Contains confidence scores and evidence.
*   **`RecurrenceCandidateEvidence`**: Links a candidate to the specific transactions that triggered the hypothesis.
*   **`UserConfirmationEvent`**: An audit log of the user accepting, rejecting, or editing a candidate.

#### Confirmed Knowledge
*   **`RecurringExpense`**: A confirmed bill with a known periodicity and amount.
*   **`RecurringIncome`**: A confirmed income source.

#### Decision Logic
*   **`ReservePolicy`**: A rule for setting aside funds (e.g., "Emergency Fund", "Tax Reserve").
*   **`ReserveInstance`**: The actual allocation of funds to a policy at a point in time.

## Contract

*   **Epistemic Separation**: This app strictly separates *guesses* (`Candidate`) from *facts* (`RecurringExpense`).
*   **Auditability**: All inferences must link back to evidence, and all confirmations must be logged.
*   **Dependency**: Depends on `finance` for raw data but adds the interpretation layer.
