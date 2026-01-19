import csv
from typing import List
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

                    # Basic validation for required columns
                    if 'entry_text' in row and 'sentence' in row:
                        sentences.append(
                            SourceSentence(
                                id=item_id,
                                entry_text=row['entry_text'],
                                sentence=row['sentence']
                            )
                        )
                    else:
                        print(f"Skipping row in CSV due to missing required columns (entry_text or sentence): {row}")
        except FileNotFoundError:
            print(f"Error: CSV file not found at {self.file_path}")
        except Exception as e:
            print(f"Error reading CSV file {self.file_path}: {e}")
        return sentences

class NoOpTaskCompletionHandler(TaskCompletionHandler):
    """
    A no-operation implementation of TaskCompletionHandler, used for
    data sources (like CSV) where there's no external task to complete or label.
    """
    def complete_task(self, task_id: str):
        print(f"No-op: Task {task_id} would be marked as complete.")

    def add_label_to_task(self, task_id: str, label_name: str):
        print(f"No-op: Label '{label_name}' would be added to task {task_id}.")
