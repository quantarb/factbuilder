# Finance App

The `finance` app manages the domain-specific data models for financial information. It serves as a data source for the facts engine.

## Main Interfaces

### Models

*   **`Account`**: Represents a financial account (e.g., bank account, credit card) belonging to a user.
*   **`BankTransaction`**: Records transactions for bank accounts. Includes details like posting date, description, amount, and balance.
*   **`CreditCardTransaction`**: Records transactions for credit card accounts. Includes transaction date, post date, description, category, and amount.

## Contract

*   **Data Storage**: This app is primarily responsible for storing raw financial data.
*   **Integration**: The `facts` app will likely query these models to compute derived facts (e.g., total spending, monthly budget status).
