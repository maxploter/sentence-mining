from abc import ABC, abstractmethod
from typing import Optional

class TaskCompletionHandler(ABC):
    """
    Abstract Base Class for handling task completion in a data source.
    This provides an interface for the core logic to signal that an item
    has been processed, without knowing the specifics of the data source.
    """
    @abstractmethod
    def complete_task(self, item_id: str):
        """Marks a task as complete in the underlying data source."""
        pass

    @abstractmethod
    def on_error(self, item_id: str, message: str, exception: Optional[Exception] = None):
      """
      Handles an error for a given item. This can involve tagging, commenting, or other actions
      depending on the specific data source.
      """
        pass
