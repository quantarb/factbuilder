# Conversations App

The `conversations` app manages the interaction between users and the system. It handles the chat interface and stores the history of messages.

## Main Interfaces

### Models

*   **`Conversation`**: Groups messages into a session. Linked to a user.
*   **`Message`**: Represents a single message in a conversation. It can be from the 'user' or 'bot'.
    *   Can be linked to a `Question` and `Answer` from the `facts` app.
    *   Can be linked to a `TaxonomyProposal` from the `agents` app if the bot is proposing a new fact.

### Views

*   **`chat.html`**: The template for the chat interface.
*   **`views.py`**: Handles the HTTP requests for the chat UI and API endpoints for sending/receiving messages.

## Contract

*   **User Interface**: Provides the front-end for users to ask questions and receive answers.
*   **Integration**: Connects user input to the `facts` engine (for answering questions) and the `agents` app (for handling unknown queries via proposals).
