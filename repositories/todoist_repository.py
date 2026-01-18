from todoist_api_python.api import TodoistAPI
import config

class TodoistRepository:
    """
    Repository for interacting with the Todoist API.
    This class is a thin wrapper around the todoist-api-python client.
    """
    def __init__(self):
        self.api = TodoistAPI(config.TODOIST_API_KEY)

    def get_project_tasks(self, project_name):
        """
        Fetches all active tasks from a specific Todoist project.
        """
        try:
            projects = self.api.get_projects()
            project = next((p for p in projects if p.name == project_name), None)

            if not project:
                print(f"Project '{project_name}' not found.")
                return []

            return self.api.get_tasks(project_id=project.id)
        except Exception as e:
            print(f"Error fetching tasks from Todoist: {e}")
            return []

    def complete_task(self, task_id):
        """
        Marks a task as complete in Todoist.
        Raises an exception if the API call fails.
        """
        try:
            is_success = self.api.close_task(task_id=task_id)
            if not is_success:
                raise Exception(f"Todoist API failed to close task {task_id}.")
            print(f"Task {task_id} completed.")
        except Exception as e:
            print(f"Error completing task {task_id}: {e}")
            raise

    def add_label_to_task(self, task_id, label_name):
        """
        Adds a label to a task in Todoist without removing existing labels.
        Raises an exception if the API call fails.
        """
        try:
            task = self.api.get_task(task_id=task_id)
            # Ensure we don't add duplicate labels
            if label_name not in task.labels:
                new_labels = task.labels + [label_name]
                is_success = self.api.update_task(task_id=task_id, labels=new_labels)
                if not is_success:
                    raise Exception(f"Todoist API failed to update task {task_id} with label '{label_name}'.")
                print(f"Added label '{label_name}' to task {task_id}.")
            else:
                print(f"Task {task_id} already has label '{label_name}'.")
        except Exception as e:
            print(f"Error adding label to task {task_id}: {e}")
            raise
