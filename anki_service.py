import re
import config
from llm_service import LLMService
from repositories.anki_repository import AnkiRepository, AnkiConnectError

class AnkiService:
    def __init__(self, anki_repository: AnkiRepository, llm_service: LLMService):
        self.repository = anki_repository
        self.llm_service = llm_service

    @staticmethod
    def _get_current_deck_name():
        return config.ANKI_DECK_NAME

    def _ensure_model(self):
        """
        Ensure the cloze model for sentence mining exists in Anki.
        """
        model_name = config.ANKI_MODEL_NAME
        names = self.repository.request("modelNames") or []

        if model_name not in names:
            css = """
            .card {
             font-family: arial;
             font-size: 20px;
             text-align: center;
             color: black;
             background-color: white;
            }
            .cloze {
             font-weight: bold;
             color: blue;
            }
            """
            params = {
                "modelName": model_name,
                "inOrderFields": [
                    "Word",       # The target word
                    "Text",       # The full text with cloze deletions
                    "Definition", # The word's definition
                    "Context",    # Original context/source
                ],
                "css": css,
                "isCloze": True,
                "cardTemplates": [
                    {
                        "Name": "Sentence Cloze",
                        "Front": "{{cloze:Text}}",
                        "Back": "{{cloze:Text}}<hr id=answer>"
                                "<b>{{Word}}</b><br><br>"
                                "{{Definition}}<br><br>"
                                "<em>Source: {{Context}}</em>"
                    }
                ],
            }
            self.repository.request("createModel", params)

    def _ensure_deck(self, deck_name: str):
        names = self.repository.request("deckNames") or []
        if deck_name not in names:
            self.repository.request("createDeck", {"deck": deck_name})

    def initialize_anki(self):
        """
        Checks connection to AnkiConnect and ensures deck and model exist.
        """
        try:
            self.repository.request("version")
            deck_name = self._get_current_deck_name()
            self._ensure_deck(deck_name)
            self._ensure_model()
        except AnkiConnectError as e:
            raise ConnectionError(f"AnkiConnect is not available: {e}")

    @staticmethod
    def _remove_cloze_syntax(text):
        """Removes Anki cloze deletion syntax (e.g., {{c1::word}}) from a string."""
        if not text:
            return ""
        return re.sub(r'\{\{c\d+::(.*?)\}\}', r'\1', text)

    def _create_cloze_sentence(self, word, sentence, cloze_number):
        """
        Creates a cloze-deleted sentence for a specific cloze number (c1, c2, etc.).
        """
        normalized_word = word.replace('‑', '-').replace('—', '-')
        normalized_sentence = sentence.replace('‑', '-').replace('—', '-')
        
        cloze_tag = f"{{{{c{cloze_number}::\\1}}}}"

        pattern_bold = f'\\*\\*({re.escape(normalized_word)})\\*\\*'
        cloze_sentence, count = re.subn(pattern_bold, cloze_tag, normalized_sentence, flags=re.IGNORECASE)

        if count == 0:
            pattern_plain = f'({re.escape(normalized_word)})'
            cloze_sentence, count = re.subn(pattern_plain, cloze_tag, normalized_sentence, flags=re.IGNORECASE)

        if count == 0:
            print(f"Regex failed for '{word}'. Trying LLM to create cloze...")
            llm_cloze = self.llm_service.create_cloze_with_llm(word, sentence)
            if '{{c1::' in llm_cloze:
                cloze_sentence = llm_cloze.replace('{{c1::', f'{{{{c{cloze_number}::')
            else:
                 cloze_sentence = sentence

        if f"c{cloze_number}::" not in cloze_sentence:
            raise ValueError(f"Failed to create a cloze for '{word}' in sentence: '{sentence}'")

        return cloze_sentence

    def add_note(self, word, definition, sentence1, sentence2, context, tags=None):
        """
        Adds a single cloze note with two sentences to Anki.
        """
        clean_word = self._remove_cloze_syntax(word)
        clean_context = self._remove_cloze_syntax(context)
        deck_name = self._get_current_deck_name()
        model_name = config.ANKI_MODEL_NAME

        query = f'"deck:{deck_name}" "note:{model_name}" "Word:{clean_word}"'
        duplicate_notes = self.repository.request("findNotes", {"query": query})
        if duplicate_notes:
            print(f"Note for '{word}' already exists. Skipping.")
            return

        try:
            cloze1 = self._create_cloze_sentence(word, sentence1, 1)
            cloze2 = self._create_cloze_sentence(word, sentence2, 2)
        except ValueError as e:
            print(e)
            raise

        full_text = f"{cloze1}<br>{cloze2}"

        note = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": {
                "Word": clean_word,
                "Text": full_text,
                "Definition": definition,
                "Context": clean_context or "",
            },
            "options": {"allowDuplicate": False},
            "tags": tags or [],
        }
        
        try:
            self.repository.request("addNote", {"note": note})
            print(f"Added note for '{word}'.")
        except AnkiConnectError as e:
            print(f"Failed to add note for '{word}': {e}")
            raise
