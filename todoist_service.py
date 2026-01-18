import re
import config
from repositories.todoist_repository import TodoistRepository

class TodoistService:
    def __init__(self, repository: TodoistRepository):
        self.repository = repository

    def get_tasks(self):
        """
        Fetches all active tasks from the specified Todoist project.
        """
        return self.repository.get_project_tasks(config.TODOIST_PROJECT_NAME)

    @staticmethod
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

    def complete_task(self, task_id):
        """
        Marks a task as complete in Todoist.
        """
        self.repository.complete_task(task_id)

    def add_label_to_task(self, task_id, label_name):
        """
        Adds a label to a task in Todoist.
        """
        self.repository.add_label_to_task(task_id, label_name)
