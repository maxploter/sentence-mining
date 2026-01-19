from dataclasses import dataclass

@dataclass
class SourceSentence:
    """
    A domain model representing a sentence "mined" from a source.
    This is an internal representation, decoupled from any specific data source.
    """
    id: str
    entry_text: str
    sentence: str
