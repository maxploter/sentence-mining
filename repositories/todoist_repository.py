import logging  # Import the logging module

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
          projects_iterator = self.api.get_projects()
          all_projects = []
          for project_list in projects_iterator:
            all_projects.extend(project_list)
          project = next((p for p in all_projects if p.name == project_name), None)

          if not project:
            logging.warning(f"Project '{project_name}' not found.")
            return []

          tasks_iterator = self.api.get_tasks(project_id=project.id)
          all_tasks = []
          for task_list in tasks_iterator:
            all_tasks.extend(task_list)
          return all_tasks
        except Exception as e:
            logging.error(f"Error fetching tasks from Todoist: {e}")
            return []

    def complete_task(self, task_id):
        """
        Marks a task as complete in Todoist.
        Raises an exception if the API call fails.
        """
        try:
          is_success = self.api.complete_task(task_id=task_id)
          if not is_success:
            raise Exception(f"Todoist API failed to close task {task_id}.")
          logging.info(f"Task {task_id} completed.")
        except Exception as e:
            logging.error(f"Error completing task {task_id}: {e}")
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
                logging.info(f"Added label '{label_name}' to task {task_id}.")
            else:
                logging.info(f"Task {task_id} already has label '{label_name}'.")
        except Exception as e:
            logging.error(f"Error adding label to task {task_id}: {e}")
            raise

    def add_comment_to_task(self, task_id: str, comment_content: str):
      """
      Adds a comment to a task in Todoist.
      """
      try:
        self.api.add_comment(task_id=task_id, content=comment_content)
        logging.info(f"Added comment to task {task_id}.")
      except Exception as e:
        logging.error(f"Error adding comment to task {task_id}: {e}")
        raise
