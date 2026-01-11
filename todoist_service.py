from todoist_api_python.api import TodoistAPI
import config
import re

def get_tasks():
    """
    Fetches all active tasks from the specified Todoist project.
    """
    api = TodoistAPI(config.TODOIST_API_KEY)
    try:
        projects_iterator = api.get_projects()
        all_projects = []
        for project_list in projects_iterator:
            all_projects.extend(project_list)

        project = next((p for p in all_projects if p.name == config.TODOIST_PROJECT_NAME), None)

        if not project:
            print(f"Project '{config.TODOIST_PROJECT_NAME}' not found.")
            return []

        tasks_iterator = api.get_tasks(project_id=project.id)
        all_tasks = []
        for task_list in tasks_iterator:
            all_tasks.extend(task_list)
        return all_tasks
    except Exception as e:
        print(f"Error fetching tasks from Todoist: {e}")
        return []

def parse_task_word(task_content):
    """
    Parses the task content to extract the word to be learned.
    Handles various formats like:
    - 'English: {word}', 'english: word'
    - 'English {word}', 'english word'
    - '{word}', 'word'
    """
    content = task_content.strip()

    # Case-insensitively remove "english:" or "english" prefix
    match = re.match(r'(?i)english\s*:?\s*', content)
    if match:
        # Get the part after the prefix
        content = content[match.end():].strip()

    # Now, check for braces '{word}'
    if content.startswith('{') and content.endswith('}'):
        return content[1:-1].strip()

    # Otherwise, the remaining content is the word
    return content


def complete_task(task_id):
    """
    Marks a task as complete in Todoist.
    Raises an exception if the API call fails.
    """
    api = TodoistAPI(config.TODOIST_API_KEY)
    try:
        is_success = api.close_task(task_id=task_id)
        if not is_success:
            raise Exception(f"Todoist API failed to close task {task_id}.")
        print(f"Task {task_id} completed.")
    except Exception as e:
        print(f"Error completing task {task_id}: {e}")
        raise

def add_label_to_task(task_id, label_name):
    """
    Adds a label to a task in Todoist without removing existing labels.
    Raises an exception if the API call fails.
    """
    api = TodoistAPI(config.TODOIST_API_KEY)
    try:
        task = api.get_task(task_id=task_id)
        # Ensure we don't add duplicate labels
        if label_name not in task.labels:
            new_labels = task.labels + [label_name]
            is_success = api.update_task(task_id=task_id, labels=new_labels)
            if not is_success:
                raise Exception(f"Todoist API failed to update task {task_id} with label '{label_name}'.")
            print(f"Added label '{label_name}' to task {task_id}.")
        else:
            print(f"Task {task_id} already has label '{label_name}'.")
    except Exception as e:
        print(f"Error adding label to task {task_id}: {e}")
        raise
