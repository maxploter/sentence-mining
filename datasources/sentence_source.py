from abc import ABC, abstractmethod
from typing import List
from domain.models import SourceSentence

class SentenceSource(ABC):
    """
    Abstract Base Class for sentence data sources.
    Defines the interface for any source that provides sentences for mining.
    """
    @abstractmethod
    def fetch_sentences(self) -> List[SourceSentence]:
        """
        Fetches a list of SourceSentence objects from the data source.
        Implementations must provide logic to connect to their specific source
        and transform raw data into SourceSentence objects.
        """
        pass
