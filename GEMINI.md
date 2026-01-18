# GEMINI.md

## Project Overview

This project is a Python-based automation script designed for language learning. Its primary function is to create Anki flashcards from words saved as tasks in a Todoist project. The script fetches tasks, uses a Large Language Model (LLM) via the Nebius AI API to generate definitions and example sentences, and then connects to a local Anki instance through the AnkiConnect add-on to create a comprehensive set of flashcards.

The workflow is as follows:
1.  Fetches tasks from a designated Todoist project.
2.  Parses a word from each task's title or description.
3.  For each word, it calls an LLM to get a context-aware definition and generate three unique example sentences.
4.  It connects to the user's running Anki application to create multiple card types for each word, including:
    *   `Word -> Definition`
    *   `Definition -> Word`
    *   Cloze deletion (gap-fill) cards for the example sentences.
    *   Multiple-choice cards for the example sentences.
5.  Successfully processed tasks in Todoist are marked as complete.

The architecture is modular, with separate services for interacting with Todoist, the LLM, and Anki. This separation of concerns makes the codebase clean and maintainable.

## Key Technologies

*   **Language:** Python 3
*   **Core Libraries:**
    *   `todoist-api-python`: For interacting with the Todoist API.
    *   `openai`: Used as a client to interact with the Nebius AI LLM API.
    *   `requests`: For making HTTP requests to the AnkiConnect server.
    *   `python-dotenv`: For managing environment variables and secrets.
    *   `tenacity`: For implementing robust retry logic on network requests.
*   **Services:**
    *   **Todoist:** Used as the input source for words to learn.
    *   **Nebius AI:** Provides the LLM for generating card content.
    *   **Anki:** The flashcard application where the final cards are created.
    *   **AnkiConnect:** An Anki add-on that exposes a local server to allow third-party applications to interact with Anki.

## Building and Running

### Prerequisites

1.  **Python 3:** Ensure you have a recent version of Python 3 installed.
2.  **Anki Desktop:** You must have the Anki application installed and running.
3.  **AnkiConnect Add-on:** You must install the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on in Anki.

### Setup and Execution

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd sentence-mining
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Copy the example `.env` file and fill in your API keys.
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file:
    ```ini
    TODOIST_API_KEY="YOUR_TODOIST_API_KEY"
    NEBIUS_API_KEY="YOUR_NEBIUS_API_KEY"
    ```

5.  **Run the Script:**
    Make sure Anki is open and running on your machine, then execute:
    ```bash
    python main.py
    ```
    The script will generate new notes in the master deck specified in `config.py` (by default `english::sentence-mining`) and tag them with the current date.

## Development Conventions

*   **Modularity:** The project is organized into distinct service modules (`todoist_service.py`, `llm_service.py`, `anki_service.py`), a configuration file (`config.py`), and a main entry point (`main.py`). This promotes clean code and separation of concerns.
*   **Configuration:** Application settings (like project names) and secrets are managed in `config.py`. Secrets are loaded from a `.env` file, which is ignored by version control.
*   **Error Handling:** The script includes error handling, especially for network operations. It uses the `tenacity` library to automatically retry failed requests to AnkiConnect and the LLM API with exponential backoff. Tasks that fail during processing (e.g., due to an inability to create a cloze) are tagged in Todoist for manual review.
*   **Linting:** The project uses `ruff` for code linting, as indicated by its inclusion in `requirements.txt`.
*   **Security:** API keys and other secrets are kept out of the source code by using a `.env` file, which is a standard security best practice.
