import random
import todoist_service
import llm_service
import anki_service
import config


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

    # 3. Pre-process tasks to gather all words for distractor generation
    all_words = []
    processed_tasks = []
    for task in tasks:
        word = todoist_service.parse_task_word(task.content)
        context = task.description

        if not word:
            if context:
                lines = context.split('\n')
                word = lines[0].strip()
                if len(lines) > 1:
                    context = '\n'.join(lines[1:]).strip()
                else:
                    context = ""
            else:
                print(f"Task '{task.content}' has no word in title or description. Skipping.")
                continue
        
        word = llm_service.strip_markdown_formatting(word)

        if word:
            all_words.append(word)
            processed_tasks.append({'task': task, 'word': word, 'context': context})

    print(f"Found {len(processed_tasks)} tasks to process.")

    # 4. Process all tasks to gather data for notes
    notes_data = []
    for item in processed_tasks:
        task = item['task']
        word = item['word']
        context = item['context']

        print(f"Processing word: {word}")

        definition = llm_service.get_definition(word, context)
        if not definition:
            print(f"Could not get definition for {word}. Skipping.")
            continue
        print(f"Definition for {word}: {definition}")

        sentences = llm_service.generate_sentences(word, definition, context)
        if not sentences or len(sentences) < 3:
            print(f"Could not generate enough sentences for {word}. Skipping.")
            continue
        print(f"Generated sentences for {word}.")

        notes_data.append({
            'word': word,
            'definition': definition,
            'sentences': sentences,
            'context': context,
            'task_id': task.id
        })

    # 5. Define batch size and create batches
    BATCH_SIZE = 3
    note_batches = [notes_data[i:i + BATCH_SIZE] for i in range(0, len(notes_data), BATCH_SIZE)]
    print(f"Created {len(note_batches)} batches of size {BATCH_SIZE}.")

    # 6. Process each batch
    for i, batch in enumerate(note_batches):
        print(f"--- Processing Batch {i+1}/{len(note_batches)} ---")
        
        # a. Create a list of all notes for the batch
        batch_notes = []
        for data in batch:
            batch_notes.append(('basic', data))
            batch_notes.append(('cloze', data))
        
        # b. Shuffle the notes within the batch
        random.shuffle(batch_notes)
        print("Shuffled notes order within the batch.")

        failed_task_ids = set()
        
        # c. Add shuffled notes to Anki
        try:
            for note_type, data in batch_notes:
                try:
                    if note_type == 'basic':
                        print(f"Adding Basic note for '{data['word']}'...")
                        anki_service.add_basic_note(data['word'], data['definition'], data['context'])
                    elif note_type == 'cloze':
                        print(f"Adding Cloze note for '{data['word']}'...")
                        anki_service.add_cloze_note(data['word'], data['sentences'], data['context'], all_words)
                except ValueError:
                    print(f"Cloze creation failed for '{data['word']}'. Tagging task for review.")
                    todoist_service.add_label_to_task(data['task_id'], config.TODOIST_ERROR_TAG)
                    failed_task_ids.add(data['task_id'])

        except Exception as e:
            # This catches critical errors like AnkiConnect being down
            print(f"A critical error occurred while adding notes in batch {i+1}. Halting. Error: {e}")
            return
        
        print("All notes in batch processed.")

        # d. Complete Todoist tasks for the batch
        for data in batch:
            if data['task_id'] not in failed_task_ids:
                try:
                    print(f"Completing task for '{data['word']}'...")
                    todoist_service.complete_task(data['task_id'])
                except Exception as e:
                    print(f"Error completing Todoist task for '{data['word']}'. Halting process. Error: {e}")
                    return
        
        print(f"--- Finished Batch {i+1}/{len(note_batches)} ---")

    print("Sentence mining process finished.")


if __name__ == "__main__":
    main()
