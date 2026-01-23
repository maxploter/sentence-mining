# Todoist to Anki Sentence Miner

This script automates the process of creating Anki flashcards from words saved in a Todoist project. It fetches tasks, gets word definitions and example sentences using an LLM, and then generates a complete Anki deck package (`.apkg`) ready for import.

## Features

- **Todoist Integration**: Pulls tasks from a specified Todoist project.
- **Flexible Word Parsing**: Extracts words from task titles like `{word}`, `English {word}`, or just `word`.
- **AI-Powered Definitions**: Uses an LLM to get context-aware definitions for each word.
*   **AI-Powered Sentence Generation**: Generates three unique example sentences for each word.
- **Anki Card Generation**: Creates multiple card types for comprehensive learning:
    - Word -> Definition
    - Definition -> Word
    - Sentence Cloze (Gap-fill)
    - Sentence Cloze (Multiple Choice)
- **Secure**: Uses a `.env` file to keep your API keys safe.
- **Automation-Ready**: Can be easily set up with a cron job to run automatically.

## Setup and Installation

Follow these steps to set up and run the project.

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-name>
```

### 2. Create and Activate a Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies.

```bash
# Create a virtual environment named 'venv'
python3 -m venv venv

# Activate the virtual environment
# On macOS and Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

Install the required Python libraries using `pip`.

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

The script loads your API keys from a `.env` file.

1.  Create a `.env` file in the project root by copying the example file:
    ```bash
    cp .env.example .env
    ```
2.  Open the `.env` file and add your API keys:
    ```
    TODOIST_API_KEY="YOUR_TODOIST_API_KEY"
    NEBIUS_API_KEY="YOUR_NEBIUS_API_KEY"
    ```

## Usage

To run the script manually, simply execute the `main.py` file:

```bash
python main.py
```

The script will generate an Anki deck file named `English Vocabulary.apkg` (or as configured in `config.py`) in the project directory.

## Automation with Cron Job

You can automate the script to run at regular intervals using a cron job.

1.  Open your crontab file for editing:
    ```bash
    crontab -e
    ```
2.  Add a new line to schedule the job. The following example runs the script every day at 7:00 AM.

    ```
    0 7 * * * /path/to/your/project/venv/bin/python /path/to/your/project/main.py
    ```

    **Important:**
    *   Replace `/path/to/your/project/` with the absolute path to this project's directory.
    *   The command specifies the Python executable inside the virtual environment (`venv/bin/python`) to ensure the correct dependencies are used.

3.  Save and exit the crontab editor. The cron job is now active.

## Development Process

This script was developed with a modular approach to separate concerns and make the code easier to maintain and extend.

1.  **Project Scaffolding**: The project structure was created with separate files for each service (`todoist_service.py`, `llm_service.py`, `anki_service.py`), a main entry point (`main.py`), and a configuration file (`config.py`).
2.  **Dependency Management**: A `requirements.txt` file was created to list all necessary libraries (`todoist-api-python`, `openai`, `genanki`, `python-dotenv`).
3.  **Configuration**: A `config.py` file was set up to handle both static configuration (like project and deck names) and secrets.
4.  **Services Implementation**:
    *   `todoist_service.py`: Implemented functions to connect to the Todoist API, fetch tasks from a specific project, and parse word from task titles.
    *   `llm_service.py`: Implemented functions to interact with the Nebius API to get definitions and generate example sentences, with carefully crafted prompts for each task.
    *   `anki_service.py`: Implemented logic to create Anki models, decks, and notes using the `genanki` library. This includes setting up different card templates, including cloze deletions.
5.  **Main Orchestrator**: The `main.py` script was created to orchestrate the entire workflow, from fetching tasks to saving the final Anki deck.
6.  **Security**: To protect sensitive API keys, the script was refactored to load secrets from a `.env` file, which is ignored by Git. `python-dotenv` was added to manage this.
7.  **Refinements**: The code was iteratively improved. For instance, the LLM API calls were updated to the latest syntax for Nebius, and the Anki cloze deletion logic was corrected to use the proper formatting.

## Anki Tagging System

The application implements a flexible tagging system for Anki notes, combining tags from multiple sources. This system utilizes a nested tag hierarchy (using `::`) for better organization and leverages Anki's powerful filtering capabilities.

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