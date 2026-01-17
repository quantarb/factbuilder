# Finance App (Level 0-1)

The `finance` app manages the domain-specific data models for **Ground Truth** financial information. It serves as the foundational data source for the facts engine.

## Role in Knowledge Ladder

*   **Level 0 (Ground Truth)**: Stores the raw "What happened" data.
*   **Level 1 (Parameterized)**: Supports queries that filter or aggregate this data (e.g., "Spending last month").

## Main Interfaces

### Models

*   **`Account`**: Represents a financial account (e.g., bank account, credit card) belonging to a user.
*   **`BankTransaction`**: Records transactions for bank accounts. Includes details like posting date, description, amount, and balance.
*   **`CreditCardTransaction`**: Records transactions for credit card accounts. Includes transaction date, post date, description, category, and amount.

## Contract

*   **Data Storage**: This app is primarily responsible for storing raw financial data.
*   **No Inference**: This app does *not* guess about recurring bills or future spending. It only records what has already cleared.
*   **Integration**: The `facts` app queries these models to compute derived facts.
