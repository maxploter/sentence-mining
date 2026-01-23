import csv
import logging  # Import the logging module
from typing import List  # Import Optional

from datasources.sentence_source import SentenceSource
from domain.models import SourceSentence


class CsvSentenceSource(SentenceSource):
    """
    A SentenceSource implementation that fetches sentences from a CSV file.
    It automatically detects the column structure based on the number of columns,
    supporting 2, 3, or 4 columns, ignoring the header row.
    - 2 columns: entry_text, sentence
    - 3 columns: id, entry_text, sentence
    - 4 columns: id, entry_text, sentence, tags
    """
    def __init__(self, file_path: str):
        self.file_path = file_path

    def fetch_sentences(self) -> List[SourceSentence]:
        """
        Reads a CSV file and converts each row into a SourceSentence object.
        It handles CSVs with 2, 3, or 4 columns, mapping them to:
        - 2 cols: entry_text, sentence
        - 3 cols: id, entry_text, sentence
        - 4 cols: id, entry_text, sentence, tags
        It assumes the first row is a header and skips it.
        """
        sentences = []
        try:
            with open(self.file_path, mode='r', newline='', encoding='utf-8') as csvfile:
              reader = csv.reader(csvfile)
              # Skip header row
              next(reader, None)

              for i, row in enumerate(reader):
                num_cols = len(row)
                # Skip empty rows
                if num_cols == 0:
                  continue

                item_id = f"csv-{i + 1}"
                entry_text = ""
                sentence = ""
                item_tags = ["Type::CSV"]

                if num_cols == 2:
                  entry_text, sentence = row
                elif num_cols == 3:
                  item_id, entry_text, sentence = row
                elif num_cols >= 4:
                  item_id, entry_text, sentence, tags_str = row[:4]
                  if tags_str:
                    item_tags.extend([tag.strip() for tag in tags_str.split(',')])
                else:
                  logging.warning(f"Skipping row in CSV due to unexpected number of columns ({num_cols}): {row}")
                  continue

                if entry_text and sentence:
                      sentences.append(
                          SourceSentence(
                              id=item_id,
                            entry_text=entry_text,
                            sentence=sentence,
                              tags=item_tags
                          )
                      )
                else:
                  logging.warning(
                    f"Skipping row in CSV due to missing entry_text or sentence after processing: {row}")

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
