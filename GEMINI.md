# GEMINI.md

## Project Overview

This project is a Python-based automation script designed for language learning, focusing on creating Anki flashcards. Its core function is to process words and sentences from various configurable sources (e.g., Todoist tasks, CSV files). For each item, it leverages a Large Language Model (LLM) via the Nebius AI API to generate context-aware definitions and additional example sentences. Finally, it connects to a local Anki instance through the AnkiConnect add-on to create a single, comprehensive Anki note per item.

Each generated Anki note contains two types of cards for versatile study:

1. A **Cloze Deletion card**, where the target word is blanked out in its original sentence and a newly generated one.
2. A **Definition -> Word card**, which prompts the user to recall the word from its definition.

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
    * `ruff`: For code linting and formatting.
    * `pytest`: For unit and integration testing.
    * `pytest-mock`: For creating mock objects in tests.
*   **Architectural Components:**
    *   **Domain Models:** Simple dataclasses (`SourceSentence`) representing the core data entities, decoupled from any specific source.
    *   **Repositories:** Abstract away the details of external APIs (Todoist, Nebius AI, AnkiConnect), providing a clean interface for services. (`TodoistRepository`, `LLMRepository`, `AnkiRepository`).
    *   **Services:** Encapsulate the application's business logic, depending on repositories for data access and LLM interactions. (`LLMService`, `AnkiService`).
    * **Data Sources:** Implement the `SentenceSource` interface to provide `SourceSentence` objects from various
      origins (e.g., `TodoistSentenceSource`, `CsvSentenceSource`, `TextFileSentenceSource`).
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
    ```
    If `DATA_SOURCE_TYPE` is set to `"csv"`, the script will look for a `words.csv` file in the project's root
    directory. The `words.csv` file should have the following header and format:
    ```csv
    id,entry_text,sentence,tags
    unique_id_1,your_word_or_phrase,The full sentence containing your word or phrase.,"Tag1,Source::BookTitle"
    unique_id_2,another_word,Another example sentence,Tag2
    ```
    *   `id`: A unique identifier for the entry (e.g., a number, a UUID).
    *   `entry_text`: The text from which the word to be learned will be extracted (e.g., "apple", "english headspace").
    *   `sentence`: The full sentence context for the word.
    * `tags` (Optional): A comma-separated string of tags to be added to the Anki note.

6.  **Run the Script:**
    Make sure Anki is open and running on your machine, then execute:
    ```bash
    python main.py [--source <todoist|csv|text_file>] [--csv-file <path>] [--text-file <path>] [--tags <tag1,tag2,...>]
    ```
    *   `--source`: Specifies the data source type. Can be `todoist` (default), `csv`, or `text_file`.
    *   `--csv-file`: Required if `--source csv` is used. Specifies the path to your CSV file (e.g., `words.csv`).
    *   `--text-file`: Required if `--source text_file` is used. Specifies the path to your plain text file (e.g., `sentences.txt`).
    *   `--tags` (`-t`): Accepts a comma-separated list of additional tags to apply to all generated Anki notes in the current run (e.g., `--tags "Topic::Literature,Critical"`). These tags will be combined with any tags provided by the data source.

    **Examples:**
    *   **Using Todoist (default):**
        ```bash
        python main.py
        ```
    *   **Using CSV file with batch tags:**
        ```bash
        python main.py --source csv --csv-file my_book.csv --tags "Source::MyBook,Topic::History"
        ```
    *   **Using a plain text file:**
        ```bash
        python main.py --source text_file --text-file my_sentences.txt --tags "Type::Reading,Functional::NewWords"
        ```
    
    The script will generate new notes in the master deck specified in `config.py` (by default `english::sentence-mining`) and tag them with the current date. Command-line arguments will override the default source type.

## Development Conventions

*   **Layered Architecture & Modularity:** The project now adheres to a layered architecture to promote clean code, separation of concerns, and testability:
    *   **Domain Layer (`domain/`)**: Contains core business entities (`SourceSentence`) and interfaces (`SentenceSource`, `TaskCompletionHandler`) that define the application's vocabulary and contracts, independent of implementation details.
    *   **Repositories Layer (`repositories/`)**: Abstracts away the details of external APIs (Todoist, Nebius AI, AnkiConnect). These are thin wrappers around external libraries, handling API calls and error retry logic.
    *   **Service Layer (`llm_service.py`, `anki_service.py`, `word_processor.py`)**: Encapsulates the application's business logic. Services operate on domain models and depend on repositories and other services via **Dependency Injection**.
    *   **Data Sources Layer (`datasources/`)**: Implements the `SentenceSource` and `TaskCompletionHandler` interfaces. These components are responsible for fetching raw data from specific sources (e.g., Todoist, CSV, Text files) and transforming it into domain models.
    * **Composition Root (`main.py`)**: Acts as the application's entry point, where all dependencies are wired
      together. It parses command-line arguments to select the appropriate data source, initializes the repositories,
      services, and data sources, and injects them where needed.
* **Logging**: A central logging configuration is set up in `main.py` to provide real-time, detailed feedback on the
  script's execution, including connection statuses, data processing, and errors.
* **Duplicate Note Handling:** The `AnkiService` implements intelligent logic for handling duplicate notes. When a note
  with the same word and definition is found:
    * If the card has been studied (i.e., its review interval is greater than zero), the note's content is overwritten
      with the new sentences, and its learning progress is **reset**.
    * If the card is new and unstudied, the new sentences are **appended** to the existing note, preserving all
      sentences collected for that word.
*   **Dependency Injection:** Dependencies are passed into constructors of classes (services, data sources) rather than being created internally. This makes components highly decoupled and significantly improves testability, as mock implementations can be easily injected during testing.
*   **Tagging System:** The application implements a flexible tagging system for Anki notes, combining tags from multiple sources. This system utilizes a nested tag hierarchy (using `::`) for better organization and leverages Anki's powerful filtering capabilities.

    **Recommended Tag Structure:**

    *   **Time**: `Year::YYYY` (e.g., `Year::2026`) and `Month::::MM` (e.g., `Month::01`). These are automatically generated.
    *   **Source Type**: `Type::Book`, `Type::News`, `Type::Podcast`, etc. (e.g., `Type::Book` from a CSV or text file, `Type::Todoist` for Todoist tasks).
    *   **Specific Source**: `Source::BookName`, `Source::NewspaperName`, `Source::PodcastName` (e.g., `Source::Harry_Potter`, `Source::New_Yorker`, `Source::NPR_Podcast`). This can be added via command-line arguments for batch processing.
    *   **Subject/Domain**: `Topic::Tech`, `Topic::Finance`, `Topic::Literature`, `Topic::History`, etc.
    *   **Functional Tags (User-Defined)**: These tags describe how the card behaves or its status.
        *   `Check`: For cards that might have a typo, an incorrect definition, or require manual review.
        *   `Idiom` or `PhrasalVerb`: To categorize multi-word expressions.
        *   `Critical`: For words or phrases that are essential to know (e.g., for work, an exam).

    **How Tagging Works:**
    *   **Combination**: Tags are collected from script-generated defaults, data source metadata (e.g., Todoist task labels, CSV `tags` column), and command-line arguments (`--tags` or `-t`).
    *   **Deduplication**: All collected tags are combined, and duplicates are automatically removed.
    *   **Hierarchical Format**: Anki's hierarchical tag format (e.g., `Parent::Child`) is used for better organization.
    *   **Benefits**: Using a robust tagging system in Anki allows for flexible study. You can create "Filtered Decks" based on specific tags (e.g., to study only words from a particular book before a test) while keeping all your cards in one main deck for daily, efficient review.

    **Example Usage (Command Line):**
    ```bash
    python main.py --source csv --csv-file my_book.csv --tags "Source::MyBook,Topic::History,Type::Book"
    python main.py --source text_file --text-file my_sentences.txt --tags "Source::Article_Title,Topic::Science,Check"
    ```
*   **Configuration:** Application settings (like project names) and secrets are managed in `config.py`. Secrets are loaded from a `.env` file, which is ignored by version control.
*   **Error Handling:** The script includes robust error handling, especially for network operations, using the `tenacity` library for automatic retries with exponential backoff. Tasks that fail during processing (e.g., due to an inability to create a cloze) are tagged in Todoist (if Todoist is the source) for manual review.
*   **Linting:** The project uses `ruff` for code linting to maintain code quality.
*   **Security:** API keys and other secrets are kept out of the source code by using a `.env` file, which is a standard security best practice.
