# GEMINI.md

## Project Overview

This project is a Python-based automation script designed for language learning, focusing on creating Anki flashcards. Its core function is to process words and sentences from various configurable sources (e.g., Todoist tasks, CSV files). For each item, it leverages a Large Language Model (LLM) via the Nebius AI API to generate context-aware definitions and additional example sentences. Finally, it connects to a local Anki instance through the AnkiConnect add-on to create a single, comprehensive Anki note per item.

Each generated Anki note consists of two cloze deletion cards, designed for effective recall:
1.  A cloze deletion card based on the original sentence where the word was encountered.
2.  A cloze deletion card based on a newly generated example sentence.

The architecture has evolved to be highly modular and testable, employing a layered approach with **Domain Models**, **Repositories**, **Services**, and **Data Sources**. This design allows for easy extension to new data input methods (like CSV files) and robust testing by abstracting external APIs and focusing on the application's business logic. Items successfully processed are marked as complete in their respective data sources where applicable (e.g., Todoist tasks are marked as complete).

## Key Technologies

*   **Language:** Python 3
*   **Core Libraries:**
    *   `todoist-api-python`: For interacting with the Todoist API (within `TodoistRepository`).
    *   `openai`: Used as a client to interact with the Nebius AI LLM API (within `LLMRepository`).
    *   `requests`: For making HTTP requests to the AnkiConnect server (within `AnkiRepository`).
    *   `python-dotenv`: For managing environment variables and secrets.
    *   `tenacity`: For implementing robust retry logic on network requests.
    *   `dataclasses`: For creating clean, domain-specific data models.
*   **Architectural Components:**
    *   **Domain Models:** Simple dataclasses (`SourceSentence`) representing the core data entities, decoupled from any specific source.
    *   **Repositories:** Abstract away the details of external APIs (Todoist, Nebius AI, AnkiConnect), providing a clean interface for services. (`TodoistRepository`, `LLMRepository`, `AnkiRepository`).
    *   **Services:** Encapsulate the application's business logic, depending on repositories for data access and LLM interactions. (`LLMService`, `AnkiService`).
    *   **Data Sources:** Implement the `SentenceSource` interface to provide `SourceSentence` objects from various origins (e.g., `TodoistSentenceSource`, `CsvSentenceSource`).
    *   **Word Processor:** A utility (`WordProcessor`) for extracting the core word to be learned from raw source text.
    *   **Task Completion Handlers:** An abstraction (`TaskCompletionHandler`) to manage marking items as processed in their respective data sources (e.g., `TodoistTaskCompletionHandler`, `NoOpTaskCompletionHandler`).
    *   **Composition Root:** `main.py` is now responsible for wiring up all dependencies (repositories, services, data sources) based on configuration.
*   **External Integrations:**
    *   **Todoist:** Can be used as an input source for words, with tasks marked as complete.
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
    
    # Configure the data source type (default: todoist)
    # Set to "csv" to use a local CSV file instead of Todoist.
    # DATA_SOURCE_TYPE="csv" 
    ```
    If `DATA_SOURCE_TYPE` is set to `"csv"`, the script will look for a `words.csv` file in the project's root directory. The `words.csv` file should have the following header and format:
    ```csv
    id,source_text,sentence
    unique_id_1,your_word_or_phrase,The full sentence containing your word or phrase.
    unique_id_2,english another_word,Another example sentence.
    ```
    *   `id`: A unique identifier for the entry (e.g., a number, a UUID).
    *   `source_text`: The text from which the word to be learned will be extracted (e.g., "apple", "english headspace").
    *   `sentence`: The full sentence context for the word.

5.  **Run the Script:**
    Make sure Anki is open and running on your machine, then execute:
    ```bash
    python main.py
    ```
    The script will generate new notes in the master deck specified in `config.py` (by default `english::sentence-mining`) and tag them with the current date.

## Development Conventions

*   **Layered Architecture & Modularity:** The project now adheres to a layered architecture to promote clean code, separation of concerns, and testability:
    *   **Domain Layer (`domain/`)**: Contains core business entities (`SourceSentence`) and interfaces (`SentenceSource`, `TaskCompletionHandler`) that define the application's vocabulary and contracts, independent of implementation details.
    *   **Repositories Layer (`repositories/`)**: Abstracts away the details of external APIs (Todoist, Nebius AI, AnkiConnect). These are thin wrappers around external libraries, handling API calls and error retry logic.
    *   **Service Layer (`llm_service.py`, `anki_service.py`, `word_processor.py`)**: Encapsulates the application's business logic. Services operate on domain models and depend on repositories and other services via **Dependency Injection**.
    *   **Data Sources Layer (`datasources/`)**: Implements the `SentenceSource` and `TaskCompletionHandler` interfaces. These components are responsible for fetching raw data from specific sources (e.g., Todoist, CSV) and transforming it into domain models.
    *   **Composition Root (`main.py`)**: Responsible for wiring up all the dependencies (repositories, services, data sources) based on configuration, and executing the main application flow.
*   **Dependency Injection:** Dependencies are passed into constructors of classes (services, data sources) rather than being created internally. This makes components highly decoupled and significantly improves testability, as mock implementations can be easily injected during testing.
*   **Configuration:** Application settings (like project names, data source type) and secrets are managed in `config.py`. Secrets are loaded from a `.env` file, which is ignored by version control.
*   **Error Handling:** The script includes robust error handling, especially for network operations, using the `tenacity` library for automatic retries with exponential backoff. Tasks that fail during processing (e.g., due to an inability to create a cloze) are tagged in Todoist (if Todoist is the source) for manual review.
*   **Linting:** The project uses `ruff` for code linting to maintain code quality.
*   **Security:** API keys and other secrets are kept out of the source code by using a `.env` file, which is a standard security best practice.
