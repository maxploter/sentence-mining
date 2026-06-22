# Todoist/CSV to Anki Sentence Miner

![banner](assets/banner.jpg)

This script automates the process of creating Anki flashcards from words saved in a Todoist project. It fetches tasks, gets word definitions and example sentences using an LLM, and then generates a complete Anki deck package (`.apkg`) ready for import.

## Features

- **Todoist Integration**: Pulls tasks from a specified Todoist project.
- **Flexible Word Parsing**: Extracts words from task titles like `{word}`, `English {word}`, or just `word`.
- **AI-Powered Definitions**: Uses an LLM to get context-aware definitions for each word.
- **AI-Powered Sentence Generation**: Generates an example sentence for each word.
- **Multi-language support**: Build decks for any language (Estonian, Russian, …) via `--learning-language`; control the language of definitions separately via `--instruction-language`.
- **Anki Card Generation**: Creates cloze-deletion flashcards via AnkiConnect.
- **Per-language subdecks**: Every language gets its own subdeck — `sentence-mining::<language>` (e.g. `sentence-mining::english`, `sentence-mining::estonian`). The root deck is an empty container.
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

    # Optional: override the Nebius model without touching code.
    # Default is openai/gpt-oss-120b (the 20b model was retired April 2026).
    NEBIUS_MODEL="openai/gpt-oss-120b"
    ```

## Usage

Make sure Anki is open and running, then execute `main.py`:

```bash
python main.py [--source <todoist|csv|text_file>] \
               [--csv-file <path>] \
               [--text-file <path>] \
               [--tags <tag1,tag2,...>] \
               [--learning-language <code|name>] \
               [--instruction-language <code|name>]
```

**Flags:**

| Flag | Default | Description |
|---|---|---|
| `--source` | `todoist` | Input source: `todoist`, `csv`, or `text_file` |
| `--csv-file` | — | Path to CSV file (required when `--source csv`) |
| `--text-file` | — | Path to text file (required when `--source text_file`) |
| `--tags` / `-t` | — | Comma-separated tags added to every note in the run |
| `--learning-language` | `english` | Language of the word and generated example sentence. Accepts ISO 639-1 codes (`en`, `et`, `ru`) or full names. |
| `--instruction-language` | `english` | Language of the definition/explanation. Accepts the same codes/names. |

**Examples:**

```bash
# Default: Todoist source, English (cron-safe, existing behavior unchanged)
python main.py

# Estonian CSV → Estonian deck + English definitions (default)
python main.py --source csv --csv-file estonian_words.csv --learning-language et

# Estonian CSV → Estonian deck + Russian definitions
python main.py --source csv --csv-file estonian_words.csv \
               --learning-language et --instruction-language ru

# English book import with tags
python main.py --source csv --csv-file my_book.csv \
               --tags "Source::MyBook,Topic::History,Type::Book"
```

Cards are created via AnkiConnect into `sentence-mining::<language>` subdecks (e.g. `sentence-mining::english`, `sentence-mining::estonian`). The root `sentence-mining` deck is an empty container.

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
python main.py --source csv --csv-file csv-files/book-project-hail-mari-until-page62.csv --tags "Source::Project_Hail_Mary,Topic::SciFi,Type::Book"
```

# Cron Job Setup Instructions

## Step 1: Make the Bash Script Executable

First, you need to give the bash script execute permissions:

```bash
chmod +x /path/to/your/project/sentence_miner_todoist.sh
```

Replace `/path/to/your/project/` with the actual path to your project directory.

## Step 2: Test the Script Manually

Before setting up the cron job, test that the script works correctly:

```bash
/path/to/your/project/sentence_miner_todoist.sh
```

This should:
1. Activate your virtual environment
2. Run the main script with the todoist source
3. Generate the Anki deck
4. Log completion to `cron.log`

## Step 3: Open Crontab Editor

Open your crontab file for editing:

```bash
crontab -e
```

If this is your first time, you may be asked to choose an editor. Select your preferred editor (nano is easiest for beginners).

## Step 4: Add the Cron Job

Add one of the following lines to schedule your job:

### Run Daily at 7:00 AM
```
0 7 * * * /path/to/your/project/sentence_miner_todoist.sh >> /path/to/your/project/cron.log 2>&1
```

### Run Every 6 Hours
```
0 */6 * * * /path/to/your/project/sentence_miner_todoist.sh >> /path/to/your/project/cron.log 2>&1
```

### Run Every Day at 10:00 PM
```
0 22 * * * /path/to/your/project/sentence_miner_todoist.sh >> /path/to/your/project/cron.log 2>&1
```

### Run Twice Daily (8 AM and 8 PM)
```
0 8,20 * * * /path/to/your/project/sentence_miner_todoist.sh >> /path/to/your/project/cron.log 2>&1
```

**Important:** Replace `/path/to/your/project/` with your actual project path in both places.

## Step 5: Save and Exit

- If using **nano**: Press `Ctrl+X`, then `Y`, then `Enter`
- If using **vim**: Press `Esc`, type `:wq`, then `Enter`

## Step 6: Verify the Cron Job

Check that your cron job was added successfully:

```bash
crontab -l
```

This should display all your scheduled cron jobs, including the one you just added.

## Understanding Cron Syntax

The cron time format is: `minute hour day month day_of_week`

```
* * * * * command
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, both 0 and 7 are Sunday)
│ │ │ └──────── Month (1-12)
│ │ └───────────── Day of month (1-31)
│ └────────────────── Hour (0-23)
└─────────────────────── Minute (0-59)
```

Examples:
- `0 7 * * *` - Every day at 7:00 AM
- `*/30 * * * *` - Every 30 minutes
- `0 */4 * * *` - Every 4 hours
- `0 9 * * 1` - Every Monday at 9:00 AM
- `0 0 1 * *` - First day of every month at midnight

## Troubleshooting

### Check if Cron is Running
```bash
sudo systemctl status cron
```

### View Cron Logs
On most systems:
```bash
grep CRON /var/log/syslog
```

Or check your project's log file:
```bash
cat /path/to/your/project/cron.log
```

### Common Issues

1. **Script doesn't run**: 
   - Verify the script has execute permissions (`chmod +x`)
   - Check that paths are absolute (not relative)
   - Ensure the `.env` file exists in the project directory

2. **Environment variables not loading**:
   - The script automatically changes to the project directory before running
   - Make sure your `.env` file is in the project root

3. **Virtual environment issues**:
   - Verify the venv exists at `venv/bin/activate`
   - Test the script manually first

### Testing Cron Job Timing

To test if your cron job will run soon, you can temporarily set it to run in a few minutes:

```bash
# Get current time
date

# Edit crontab
crontab -e

# Add a test job that runs 2 minutes from now
# For example, if it's 14:30, add:
32 14 * * * /path/to/your/project/sentence_miner_todoist.sh >> /path/to/your/project/cron.log 2>&1

# Wait and check the log file
tail -f /path/to/your/project/cron.log
```

## Disabling the Cron Job

If you need to temporarily disable the cron job:

```bash
crontab -e
```

Then add a `#` at the beginning of the line to comment it out:

```
# 0 7 * * * /path/to/your/project/sentence_miner_todoist.sh >> /path/to/your/project/cron.log 2>&1
```

To completely remove all cron jobs:

```bash
crontab -r
```

(Use with caution! This removes ALL your cron jobs.)

## Additional Tips

1. **Email Notifications**: By default, cron sends email on errors. To disable:
   ```
   MAILTO=""
   0 7 * * * /path/to/your/project/sentence_miner_todoist.sh >> /path/to/your/project/cron.log 2>&1
   ```

2. **Multiple Environments**: If you have multiple Python projects, each should have its own bash script pointing to its own venv.

3. **Backup Your Decks**: Consider setting up a separate cron job to backup your generated `.apkg` files periodically.