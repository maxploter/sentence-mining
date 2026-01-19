from abc import ABC, abstractmethod

class TaskCompletionHandler(ABC):
    """
    Abstract Base Class for handling task completion in a data source.
    This provides an interface for the core logic to signal that an item
    has been processed, without knowing the specifics of the data source.
    """
    @abstractmethod
    def complete_task(self, task_id: str):
        """Marks a task as complete in the underlying data source."""
        pass

    @abstractmethod
    def add_label_to_task(self, task_id: str, label_name: str):
        """Adds a label to a task in the underlying data source."""
        pass
