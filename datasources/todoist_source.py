from typing import List, Optional

import config
from datasources.sentence_source import SentenceSource
from domain.models import SourceSentence
from domain.task_completion_handler import TaskCompletionHandler
from repositories.todoist_repository import TodoistRepository


class TodoistSentenceSource(SentenceSource):
    """
    A SentenceSource implementation that fetches sentences from Todoist tasks.
    It uses the TodoistRepository to get raw tasks and transforms them
    into SourceSentence domain objects.
    """
    def __init__(self, repository: TodoistRepository):
        self.repository = repository

    def fetch_sentences(self) -> List[SourceSentence]:
        """
        Fetches tasks from Todoist and converts them into SourceSentence objects.
        """
        todoist_tasks = self.repository.get_project_tasks(config.TODOIST_PROJECT_NAME)
        
        sentences = []
        for task in todoist_tasks:

            # In this setup, the task.content is the raw text to parse the word from
            # and task.description is the full sentence context.
            # Extract Todoist labels as tags
            task_tags = [f"TaskLabel::{label}" for label in task.labels]
            # Add a default source type tag
            task_tags.append("Type::Todoist")

            sentences.append(
                SourceSentence(
                    id=task.id,
                    entry_text=task.content,
                    sentence=task.description,
                    tags=task_tags
                )
            )
        return sentences

class TodoistTaskCompletionHandler(TaskCompletionHandler):
    """
    An implementation of TaskCompletionHandler for Todoist.
    It uses the TodoistRepository to complete tasks and add labels.
    """
    def __init__(self, repository: TodoistRepository):
        self.repository = repository

    def complete_task(self, task_id: str):
        self.repository.complete_task(task_id)

    def on_error(self, item_id: str, message: str, exception: Optional[Exception] = None):
      """
      Handles an error for a given Todoist task.
      It adds the configured error tag and a comment with the error message to the task.
      """
      self.repository.add_label_to_task(item_id, config.TODOIST_ERROR_TAG)
      full_message = f"Processing Error: {message}"
      if exception:
        full_message += f" Details: {exception}"
      self.repository.add_comment_to_task(item_id, full_message)
