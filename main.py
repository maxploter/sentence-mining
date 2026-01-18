import datetime
import config
from todoist_service import TodoistService
from llm_service import LLMService
from anki_service import AnkiService
from repositories.todoist_repository import TodoistRepository
from repositories.llm_repository import LLMRepository
from repositories.anki_repository import AnkiRepository

def run_process(todoist_service: TodoistService, llm_service: LLMService, anki_service: AnkiService):
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

    # 2. Fetch tasks from Todoist
    tasks = todoist_service.get_tasks()
    if not tasks:
        print("No tasks found in Todoist. Exiting.")
        return
    
    print(f"Found {len(tasks)} tasks to process.")

    # 3. Process each task
    for task in tasks:
        print(f"--- Processing task: {task.content} ---")

        # a. Parse word and context from task
        word = todoist_service.parse_task_word(task.content)
        sentence1 = task.description
        source_context = task.content # For the 'Context' field in Anki

        if not word:
            if sentence1:
                lines = sentence1.split('\n')
                word = lines[0].strip()
                sentence1 = '\n'.join(lines[1:]).strip()
            else:
                print(f"Task '{task.content}' has no word in title or description. Skipping.")
                continue
        
        word = llm_service.strip_markdown_formatting(word)

        if not sentence1:
            print(f"Task for '{word}' has no context sentence in description. Skipping.")
            continue

        print(f"Processing word: '{word}'")

        # b. Get definition from LLM
        definition = llm_service.get_definition(word, sentence1)
        if not definition:
            print(f"Could not get definition for '{word}'. Skipping.")
            continue
        print(f"Definition: {definition}")

        # c. Generate second sentence from LLM
        sentence2 = llm_service.generate_sentence(word, definition, sentence1)
        if not sentence2:
            print(f"Could not generate a sentence for '{word}'. Skipping.")
            continue
        print(f"Generated sentence: {sentence2}")

        # d. Add note to Anki
        try:
            anki_service.add_note(
                word,
                definition,
                sentence1,
                sentence2,
                source_context,
                tags=date_tags
            )
        except ValueError:
            print(f"Cloze creation failed for '{word}'. Tagging task for review.")
            todoist_service.add_label_to_task(task.id, config.TODOIST_ERROR_TAG)
            continue
        except Exception as e:
            print(f"A critical error occurred while adding note for '{word}'. Halting. Error: {e}")
            return

        # e. Complete Todoist task
        try:
            print(f"Completing task for '{word}'...")
            todoist_service.complete_task(task.id)
        except Exception as e:
            print(f"Error completing Todoist task for '{word}'. Halting. Error: {e}")
            return

        print(f"--- Finished task for '{word}' ---")

    print("Sentence mining process finished.")

def main():
    """
    Composition root of the application.
    Initializes repositories and services and runs the main process.
    """
    # Initialize repositories
    todoist_repo = TodoistRepository()
    llm_repo = LLMRepository()
    anki_repo = AnkiRepository()

    # Initialize services with injected repositories
    llm_service = LLMService(llm_repo)
    todoist_service = TodoistService(todoist_repo)
    anki_service = AnkiService(anki_repo, llm_service) # AnkiService needs LLMService

    # Run the main process
    run_process(todoist_service, llm_service, anki_service)
