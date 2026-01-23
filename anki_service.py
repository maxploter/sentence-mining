import logging  # Import the logging module
import re

import config
from llm_service import LLMService
from repositories.anki_repository import AnkiRepository, AnkiConnectError


class DuplicateNoteError(Exception):
  def __init__(self, message, note_id=None):
    super().__init__(message)
    self.note_id = note_id

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
        logging.info(f"Ensuring Anki model '{config.ANKI_MODEL_NAME}' exists.")
        model_name = config.ANKI_MODEL_NAME
        names = self.repository.request("modelNames") or []

        if model_name not in names:
            logging.info(f"Anki model '{model_name}' not found. Creating it.")
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
                  "Text",  # The full text with cloze deletions (just the current one)
                    "Definition", # The word's definition
                ],
                "css": css,
                "isCloze": True,
                "cardTemplates": [
                    {
                        "Name": "Sentence Cloze",
                        "Front": "{{cloze:Text}}",
                        "Back": "{{cloze:Text}}<hr id=answer>"
                                "<b>{{Word}}</b><br><br>"
                                "{{Definition}}",
                    },
                ],
            }
            self.repository.request("createModel", params)
            logging.info(f"Anki model '{model_name}' created successfully.")
        else:
            logging.info(f"Anki model '{model_name}' already exists.")

    def _ensure_deck(self, deck_name: str):
        logging.info(f"Ensuring Anki deck '{deck_name}' exists.")
        names = self.repository.request("deckNames") or []
        if deck_name not in names:
            logging.info(f"Anki deck '{deck_name}' not found. Creating it.")
            self.repository.request("createDeck", {"deck": deck_name})
            logging.info(f"Anki deck '{deck_name}' created successfully.")
        else:
            logging.info(f"Anki deck '{deck_name}' already exists.")

    def initialize_anki(self):
        """
        Checks connection to AnkiConnect and ensures deck and model exist.
        """
        try:
            logging.info("Checking AnkiConnect connection...")
            self.repository.request("version")
            logging.info("AnkiConnect connection successful.")
            deck_name = self._get_current_deck_name()
            self._ensure_deck(deck_name)
            self._ensure_model()
        except AnkiConnectError as e:
            logging.error(f"AnkiConnect is not available: {e}")
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
            logging.info(f"Regex failed to create cloze for '{word}'. Trying LLM...")
            llm_cloze = self.llm_service.create_cloze_with_llm(word, sentence)
            if '{{c1::' in llm_cloze:
                cloze_sentence = llm_cloze.replace('{{c1::', f'{{{{c{cloze_number}::')
            else:
                 cloze_sentence = sentence
                 logging.warning(f"LLM also failed to create cloze for '{word}' in sentence: '{sentence}'. Falling back to original sentence.")


        if f"c{cloze_number}::" not in cloze_sentence:
            error_msg = f"Failed to create a cloze for '{word}' in sentence: '{sentence}'"
            logging.error(error_msg)
            raise ValueError(error_msg)

        return cloze_sentence

    def add_note(self, word, definition, sentence1, sentence2, tags=None):
        """
        Adds a new Anki note. If a duplicate (same Word and Definition) is found,
        it raises a DuplicateNoteError.
        """
        clean_word = self._remove_cloze_syntax(word)
        clean_definition = definition.replace('"', '')
        deck_name = self._get_current_deck_name()
        model_name = config.ANKI_MODEL_NAME

        # --- 1. Generate new cloze sentences ---
        new_text_block = ""
        try:
          cloze1 = self._create_cloze_sentence(word, sentence1, 1) if sentence1 else None
          cloze2 = self._create_cloze_sentence(word, sentence2, 1) if sentence2 else None
          if cloze1 and cloze2:
            new_text_block = f"{cloze1}<br>{cloze2}"
          elif cloze1:
            new_text_block = cloze1
          elif cloze2:
            new_text_block = cloze2
        except ValueError as e:
          logging.error(f"Error creating cloze sentences for '{word}': {e}")
          raise  # Re-raise to be handled in the main loop

        if not new_text_block:
          logging.warning(f"No valid sentences to process for word '{word}'.")
          return

        # --- 2. Check for duplicates ---
        query = f'"deck:{deck_name}" "note:{model_name}" "Word:{clean_word}" "Definition:{clean_definition}"'
        duplicate_notes = self.repository.request("findNotes", {"query": query})

        try:
          if duplicate_notes:
            raise DuplicateNoteError(f"Duplicate note found for word: '{clean_word}'", note_id=duplicate_notes[0])

          # --- No duplicate found: Create a new note ---
          note = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": {
              "Word": clean_word,
              "Text": new_text_block,
              "Definition": definition,
            },
            "options": {"allowDuplicate": False},
            "tags": tags or [],
          }
          self.repository.request("addNote", {"note": note})
          logging.info(f"Added new note for '{word}'.")

        except AnkiConnectError as e:
          logging.error(f"Failed to add note for '{word}': {e}")
          raise e
