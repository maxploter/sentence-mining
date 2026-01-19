import re

class WordProcessor:
    """
    A service that processes text to extract the word to be learned.
    This class encapsulates the business logic for parsing the word.
    """
    @staticmethod
    def extract_word(text_to_process: str) -> str:
        """
        Parses the task content to extract the word to be learned.
        Handles various formats like:
        - 'English: {word}', 'english: word'
        - 'English {word}', 'english word'
        - '{word}', 'word'
        """
        content = text_to_process.strip()

        # Case-insensitively remove "english:" or "english" prefix
        match = re.match(r'(?i)english\s*:?\s*', content)
        if match:
            # Get the part after the prefix
            content = content[match.end():].strip()

        # Now, check for braces '{word}'
        if content.startswith('{') and content.endswith('}'):
            return content[1:-1].strip()

        # Otherwise, the remaining content is the word
        return content
