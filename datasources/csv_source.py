import csv
import logging  # Import the logging module
from typing import List, Optional  # Import Optional

from datasources.sentence_source import SentenceSource
from domain.models import SourceSentence
from domain.task_completion_handler import TaskCompletionHandler


class CsvSentenceSource(SentenceSource):
    """
    A SentenceSource implementation that fetches sentences from a CSV file.
    The CSV file is expected to have 'id', 'entry_text', and 'sentence' columns.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path

    def fetch_sentences(self) -> List[SourceSentence]:
        """
        Reads a CSV file and converts each row into a SourceSentence object.
        """
        sentences = []
        try:
            with open(self.file_path, mode='r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for i, row in enumerate(reader):
                    # Use provided ID or generate one if not present
                    item_id = row.get('id', f"csv-{i+1}") 

                    # Parse optional tags column
                    item_tags = []
                    if 'tags' in row and row['tags']:
                        item_tags.extend([tag.strip() for tag in row['tags'].split(',')])
                    item_tags.append("Type::CSV") # Add default source type tag

                    # Basic validation for required columns
                    if 'entry_text' in row and 'sentence' in row:
                        sentences.append(
                            SourceSentence(
                                id=item_id,
                                entry_text=row['entry_text'],
                                sentence=row['sentence'],
                                tags=item_tags
                            )
                        )
                    else:
                        logging.warning(f"Skipping row in CSV due to missing required columns (entry_text or sentence): {row}")
        except FileNotFoundError:
            logging.error(f"Error: CSV file not found at {self.file_path}")
        except Exception as e:
            logging.error(f"Error reading CSV file {self.file_path}: {e}")
        return sentences

class NoOpTaskCompletionHandler(TaskCompletionHandler):
    """
    A no-operation implementation of TaskCompletionHandler, used for
    data sources (like CSV) where there's no external task to complete or label.
    """

    def complete_task(self, item_id: str):  # Changed task_id to item_id for consistency
      logging.info(f"No-op: Task {item_id} would be marked as complete.")

    def on_error(self, item_id: str, message: str, exception: Optional[Exception] = None):
      """
      Handles an error for a given item in a no-op manner.
      """
      log_message = f"No-op Error for item {item_id}: {message}"
      if exception:
        log_message += f" Details: {exception}"
      logging.warning(log_message)
