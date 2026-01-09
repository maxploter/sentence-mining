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
    (Placeholder for now)
    """
    # api = TodoistAPI(config.TODOIST_API_KEY)
    # try:
    #     api.close_task(task_id=task_id)
    #     print(f"Task {task_id} completed.")
    # except Exception as e:
    #     print(f"Error completing task {task_id}: {e}")
    pass
