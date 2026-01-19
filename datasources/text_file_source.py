import re
from typing import List
import logging # Import the logging module
from datasources.sentence_source import SentenceSource
from domain.models import SourceSentence
from datasources.csv_source import NoOpTaskCompletionHandler # Import from csv_source

class TextFileSentenceSource(SentenceSource):
    """
    A SentenceSource implementation that fetches sentences from a plain text file.
    Each line in the file is treated as a sentence. The word to be learned
    is expected to be enclosed in double asterisks (e.g., "**word**").
    """
    def __init__(self, file_path: str):
        self.file_path = file_path

    def fetch_sentences(self) -> List[SourceSentence]:
        sentences = []
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    clean_line = line.strip()
                    if not clean_line:
                        continue

                    # The entry_text is the raw line including any markdown for the word.
                    # The sentence is the line with the markdown removed, to be used as context.
                    # The WordProcessor will handle extracting the word from entry_text.
                    sentence_without_asterisks = re.sub(r'\*\*([^*]+?)\*\*', r'\1', clean_line)

                    sentences.append(
                        SourceSentence(
                            id=f"textfile-{i+1}",
                            entry_text=clean_line,
                            sentence=sentence_without_asterisks,
                            tags=["Type::TextFile"] # Add default tag
                        )
                    )
        except FileNotFoundError:
            logging.error(f"Error: Text file not found at {self.file_path}")
        except Exception as e:
            logging.error(f"Error reading text file {self.file_path}: {e}")
        return sentences
