import argparse
import datetime
import logging  # Import the logging module
from typing import Optional, List

import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from llm_service import LLMService
from anki_service import AnkiService
from word_processor import WordProcessor 

# Import repositories
from repositories.todoist_repository import TodoistRepository
from repositories.llm_repository import LLMRepository
from repositories.anki_repository import AnkiRepository

# Import data sources and completion handlers
from datasources.sentence_source import SentenceSource
from datasources.todoist_source import TodoistSentenceSource, TodoistTaskCompletionHandler
from datasources.csv_source import CsvSentenceSource, NoOpTaskCompletionHandler
from datasources.text_file_source import TextFileSentenceSource # Import the new text file source
from domain.task_completion_handler import TaskCompletionHandler


def run_process(
    sentence_source: SentenceSource,
    word_processor: WordProcessor,
    llm_service: LLMService,
    anki_service: AnkiService,
    task_completion_handler: TaskCompletionHandler,
    cli_tags: Optional[List[str]] = None, # New argument for CLI tags
):
    """
    Main function to run the sentence mining process.
    """
    logging.info("Starting sentence mining process...")

    # 1. Initialize Anki service
    try:
        anki_service.initialize_anki()
    except ConnectionError as e:
        logging.error(f"AnkiConnect initialization failed: {e}. Exiting.")
        return

    # Generate script-generated tags (e.g., Year, Month)
    now = datetime.datetime.now()
    script_generated_tags = [f"Year::{now.year}", f"Month::{now.month:02d}"]

    # 2. Fetch sentences from the data source
    mined_sentences = sentence_source.fetch_sentences()
    if not mined_sentences:
        logging.info("No sentences found from the data source. Exiting.")
        return
    
    logging.info(f"Found {len(mined_sentences)} sentences to process.")

    # 3. Process each sentence
    for item in mined_sentences:
        logging.info(f"--- Processing item: {item.entry_text} ---")

        word = word_processor.extract_word(item.entry_text)
        sentence1 = item.sentence

        # Fallback logic for word extraction if WordProcessor doesn't find it explicitly.
        # This part of the logic needs to ensure it gets a valid word for processing.
        if not word:
            # If entry_text was just a sentence without explicit word markers,
            # and sentence1 (context) exists, try to take the first meaningful word
            # or handle as an error if no clear word can be derived.
            if sentence1:
                # Simple heuristic: take the first word from the sentence as a fallback
                # This is a very basic fallback and might need more sophistication
                first_word_match = re.match(r'^\b(\w+)\b', sentence1)
                if first_word_match:
                    word = first_word_match.group(1)
                else:
                    logging.warning(f"Could not extract a meaningful word from '{item.entry_text}' or '{sentence1}'. Skipping item {item.id}.")
                    task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
                    continue
            else:
                logging.warning(f"Could not extract word from '{item.entry_text}' and no context sentence. Skipping item {item.id}.")
                task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
                continue
        
        clean_word = llm_service.strip_markdown_formatting(word)

        # Remove the block that skips items without a sentence.
        # The AnkiService will now handle the case where only an LLM-generated sentence is available.
        # if not sentence1:
        #     logging.warning(f"Item for '{clean_word}' (ID: {item.id}) has no context sentence. Skipping.")
        #     task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
        #     continue

        logging.info(f"Processing word: '{clean_word}'")

        # Combine all tags: script-generated, data source-provided, and CLI
        final_tags = set(script_generated_tags)
        if item.tags:
            final_tags.update(item.tags)
        if cli_tags:
            final_tags.update(cli_tags)
        
        # Convert set back to list for Anki
        final_tags_list = list(final_tags)

        # b. Get definition from LLM
        definition = llm_service.get_definition(clean_word, sentence1)
        if not definition:
            logging.warning(f"Could not get definition for '{clean_word}' (ID: {item.id}). Skipping.")
            task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
            continue
        logging.info(f"Definition for '{clean_word}': {definition}")

        # c. Generate second sentence from LLM
        sentence2 = llm_service.generate_sentence(clean_word, definition, sentence1)
        if not sentence2:
            logging.warning(f"Could not generate a sentence for '{clean_word}' (ID: {item.id}). Skipping.")
            task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
            continue
        logging.info(f"Generated sentence for '{clean_word}'.")

        # d. Add note to Anki
        try:
            anki_service.add_note(
                clean_word,
                definition,
                sentence1,
                sentence2,
                tags=final_tags_list # Pass combined tags
            )
        except ValueError as e:
            logging.warning(f"Cloze creation failed for '{clean_word}' (ID: {item.id}): {e}. Tagging task for review.")
            task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
            continue
        except ConnectionError as e:
            # This catches critical errors like AnkiConnect being down during add_note
            logging.error(f"A critical AnkiConnect error occurred while adding note for '{clean_word}' (ID: {item.id}). Halting. Error: {e}")
            return
        except Exception as e:
            logging.error(f"An unexpected error occurred while adding note for '{clean_word}' (ID: {item.id}): {e}. Tagging task for review.")
            task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
            continue


        # e. Complete task in data source
        try:
            logging.info(f"Completing task for '{clean_word}' (ID: {item.id})...")
            task_completion_handler.complete_task(item.id)
        except Exception as e:
            logging.error(f"Error completing task for '{clean_word}' (ID: {item.id}): {e}. Halting.")
            return

        logging.info(f"--- Finished item for '{clean_word}' ---")

    logging.info("Sentence mining process finished.")


def main():
    """
    Composition root of the application.
    Initializes repositories, services, data sources, and runs the main process.
    """
    parser = argparse.ArgumentParser(description="Create Anki flashcards from various sources.")
    parser.add_argument(
        '--source',
        type=str,
        choices=['todoist', 'csv', 'text_file'], # Added 'text_file'
        default='todoist', # Default to 'todoist' if --source is not provided
        help='Specify the data source type (e.g., todoist, csv, text_file).'
    )
    parser.add_argument(
        '--csv-file',
        type=str,
        help='Specify the path to the CSV file if --source csv is used.'
    )
    parser.add_argument( # New argument for text file
        '--text-file',
        type=str,
        help='Specify the path to the text file if --source text_file is used.'
    )
    parser.add_argument( # New argument for user-defined tags
        '--tags', '-t',
        type=str,
        help='Comma-separated tags to add to generated Anki notes (e.g., "Topic::Literature,Critical").'
    )
    args = parser.parse_args()

    # 0. Initialize Repositories (infrastructure layer)
    todoist_repo = TodoistRepository()
    llm_repo = LLMRepository()
    anki_repo = AnkiRepository()

    # 1. Initialize Services (application layer - business logic)
    word_processor = WordProcessor()
    llm_service = LLMService(llm_repo)
    # AnkiService needs both AnkiRepository and LLMService for cloze fallback
    anki_service = AnkiService(anki_repo, llm_service) 

    # 2. Initialize SentenceSource and TaskCompletionHandler based on arguments
    sentence_source: SentenceSource
    task_completion_handler: TaskCompletionHandler

    if args.source == "todoist":
        sentence_source = TodoistSentenceSource(todoist_repo)
        task_completion_handler = TodoistTaskCompletionHandler(todoist_repo)
    elif args.source == "csv":
        sentence_source = CsvSentenceSource(args.csv_file)
        task_completion_handler = NoOpTaskCompletionHandler()
    elif args.source == "text_file": # New case for text file
        sentence_source = TextFileSentenceSource(args.text_file)
        task_completion_handler = NoOpTaskCompletionHandler()
    else:
        # This should ideally not be reached due to argparse 'choices'
        raise ValueError(f"Unknown DATA_SOURCE_TYPE: {args.source}")

    # Parse CLI tags
    cli_tags_list = [tag.strip() for tag in args.tags.split(',')] if args.tags else None

    # 3. Run the main process with all wired-up components
    run_process(
        sentence_source,
        word_processor,
        llm_service,
        anki_service,
        task_completion_handler,
        cli_tags=cli_tags_list, # Pass CLI tags to run_process
    )

if __name__ == "__main__":
    main()

