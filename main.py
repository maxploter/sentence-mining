import datetime
import config
import argparse 
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
):
    """
    Main function to run the sentence mining process.
    """
    print("Starting sentence mining process...")

    # 1. Initialize Anki service
    try:
        anki_service.initialize_anki()
    except ConnectionError as e:
        print(e)
        return

    # Generate date tags for the current run
    now = datetime.datetime.now()
    date_tags = [f"Year::{now.year}", f"Month::{now.month:02d}"]

    # 2. Fetch sentences from the data source
    mined_sentences = sentence_source.fetch_sentences()
    if not mined_sentences:
        print("No sentences found from the data source. Exiting.")
        return
    
    print(f"Found {len(mined_sentences)} sentences to process.")

    # 3. Process each sentence
    for item in mined_sentences:
        print(f"--- Processing item: {item.entry_text} ---")

        word = word_processor.extract_word(item.entry_text)
        sentence1 = item.sentence
        source_context = item.entry_text

        if not word:
            # Fallback for when word is not found by WordProcessor
            # The current WordProcessor should always find a word if **word** is present
            # or if it matches "english: word" pattern, otherwise it returns the whole entry_text.
            # This 'if not word' block might need refinement based on exact WordProcessor behavior.
            print(f"Could not extract word from '{item.entry_text}'. Skipping.")
            task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
            continue
        
        # Note: strip_markdown_formatting is a static method of LLMService
        clean_word = llm_service.strip_markdown_formatting(word)

        if not sentence1:
            print(f"Item for '{clean_word}' has no context sentence. Skipping.")
            task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
            continue

        print(f"Processing word: '{clean_word}'")

        # b. Get definition from LLM
        definition = llm_service.get_definition(clean_word, sentence1)
        if not definition:
            print(f"Could not get definition for '{clean_word}'. Skipping.")
            task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
            continue
        print(f"Definition: {definition}")

        # c. Generate second sentence from LLM
        sentence2 = llm_service.generate_sentence(clean_word, definition, sentence1)
        if not sentence2:
            print(f"Could not generate a sentence for '{clean_word}'. Skipping.")
            task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
            continue
        print(f"Generated sentence: {sentence2}")

        # d. Add note to Anki
        try:
            anki_service.add_note(
                clean_word,
                definition,
                sentence1,
                sentence2,
                source_context,
                tags=date_tags
            )
        except ValueError as e:
            print(f"Cloze creation failed for '{clean_word}': {e}. Tagging task for review.")
            task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
            continue
        except ConnectionError as e:
            # This catches critical errors like AnkiConnect being down during add_note
            print(f"A critical AnkiConnect error occurred while adding note for '{clean_word}'. Halting. Error: {e}")
            return
        except Exception as e:
            print(f"An unexpected error occurred while adding note for '{clean_word}': {e}. Tagging task for review.")
            task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
            continue


        # e. Complete task in data source
        try:
            print(f"Completing task for '{clean_word}' (ID: {item.id})...")
            task_completion_handler.complete_task(item.id)
        except Exception as e:
            print(f"Error completing task for '{clean_word}' (ID: {item.id}). Halting. Error: {e}")
            return

        print(f"--- Finished item for '{clean_word}' ---")

    print("Sentence mining process finished.")


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
        default='words.csv', # Default CSV file name
        help='Specify the path to the CSV file if --source csv is used.'
    )
    parser.add_argument( # New argument for text file
        '--text-file',
        type=str,
        default='sentences.txt', # Default text file name
        help='Specify the path to the text file if --source text_file is used.'
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

    # 3. Run the main process with all wired-up components
    run_process(
        sentence_source,
        word_processor,
        llm_service,
        anki_service,
        task_completion_handler,
    )

if __name__ == "__main__":
    main()

