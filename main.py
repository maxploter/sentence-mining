import datetime
import config
from llm_service import LLMService
from anki_service import AnkiService
from word_processor import WordProcessor # Renamed from todoist_service

# Import repositories
from repositories.todoist_repository import TodoistRepository
from repositories.llm_repository import LLMRepository
from repositories.anki_repository import AnkiRepository

# Import data sources and completion handlers
from datasources.sentence_source import SentenceSource
from datasources.todoist_source import TodoistSentenceSource, TodoistTaskCompletionHandler
from datasources.csv_source import CsvSentenceSource, NoOpTaskCompletionHandler
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
        print(f"--- Processing item: {item.source_text} ---")

        word = word_processor.extract_word(item.source_text)
        sentence1 = item.sentence
        source_context = item.source_text

        if not word:
            # This case should ideally be handled by WordProcessor or input validation
            # but as a fallback, we skip if word extraction fails.
            print(f"Could not extract word from '{item.source_text}'. Skipping.")
            task_completion_handler.add_label_to_task(item.id, config.TODOIST_ERROR_TAG)
            continue
        
        # Note: strip_markdown_formatting is a static method of LLMService
        # it can be called directly, but we pass llm_service instance
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
    # 0. Initialize Repositories (infrastructure layer)
    todoist_repo = TodoistRepository()
    llm_repo = LLMRepository()
    anki_repo = AnkiRepository()

    # 1. Initialize Services (application layer - business logic)
    word_processor = WordProcessor()
    llm_service = LLMService(llm_repo)
    # AnkiService needs both AnkiRepository and LLMService for cloze fallback
    anki_service = AnkiService(anki_repo, llm_service) 

    # 2. Initialize SentenceSource and TaskCompletionHandler (data source layer)
    sentence_source: SentenceSource
    task_completion_handler: TaskCompletionHandler

    if config.DATA_SOURCE_TYPE == "todoist":
        sentence_source = TodoistSentenceSource(todoist_repo)
        task_completion_handler = TodoistTaskCompletionHandler(todoist_repo)
    elif config.DATA_SOURCE_TYPE == "csv":
        # For CSV, we need to specify the file path
        sentence_source = CsvSentenceSource("words.csv") # Assuming words.csv in root
        task_completion_handler = NoOpTaskCompletionHandler()
    else:
        raise ValueError(f"Unknown DATA_SOURCE_TYPE: {config.DATA_SOURCE_TYPE}")

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

