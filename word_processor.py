import re

class WordProcessor:
    """
    A service that processes text to extract the word to be learned.
    This class encapsulates the business logic for parsing the word.
    """
    @staticmethod
    def extract_word(entry_text: str) -> str:
        """
        Parses the entry text to extract the word to be learned.
        It first looks for words enclosed in double asterisks (**word**).
        If not found, it handles formats like:
        - 'English: {word}', 'english: word'
        - 'English {word}', 'english word'
        - '{word}', 'word'
        """
        content = entry_text.strip()

        # First, try to extract word enclosed in double asterisks
        match_asterisks = re.search(r'\*\*([^*]+?)\*\*', content)
        if match_asterisks:
            return match_asterisks.group(1).strip()

        # If no asterisks, fall back to previous logic (prefixes and braces)
        # Case-insensitively remove "english:" or "english" prefix
        match_prefix = re.match(r'(?i)english\s*:?\s*', content)
        if match_prefix:
            content = content[match_prefix.end():].strip()

        # Now, check for braces '{word}'
        if content.startswith('{') and content.endswith('}'):
            return content[1:-1].strip()

        # Otherwise, the remaining content is the word
        return content
