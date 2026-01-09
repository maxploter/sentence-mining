import todoist_service
import llm_service
import anki_service


def main():
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

    # 2. Fetch tasks from Todoist
    tasks = todoist_service.get_tasks()
    if not tasks:
        print("No tasks found in Todoist. Exiting.")
        return

    print(f"Found {len(tasks)} tasks to process.")

    # 3. Process each task
    for task in tasks:
        word = todoist_service.parse_task_word(task.content)
        context = task.description
        print(f"Processing word: {word}")

        # 4. Get definition from LLM
        definition = llm_service.get_definition(word, context)
        if not definition:
            print(f"Could not get definition for {word}. Skipping.")
            continue
        print(f"Definition for {word}: {definition}")

        # 5. Generate sentences from LLM
        sentences = llm_service.generate_sentences(word, definition, context)
        if not sentences or len(sentences) < 3:
            print(f"Could not generate enough sentences for {word}. Skipping.")
            continue
        print(f"Generated sentences for {word}.")

        # 6. Add note to Anki
        anki_service.add_note(word, definition, sentences, context)
        print(f"Added note for {word} to Anki deck.")

        # 7. Complete the task in Todoist (optional, uncomment to enable)
        # todoist_service.complete_task(task.id)
        # print(f"Completed task for {word} in Todoist.")

    print("Sentence mining process finished.")


if __name__ == "__main__":
    main()
