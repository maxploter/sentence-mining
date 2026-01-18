import config
import re
import requests
import llm_service
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception

class AnkiConnectError(Exception):
    """Custom exception for AnkiConnect errors."""
    pass

# ---------------------------
# AnkiConnect helpers
# ---------------------------

def get_current_deck_name():
    return config.ANKI_DECK_NAME

def is_retryable(exception):
    """Return True if we should retry on a timeout or network error."""
    error_str = str(exception).lower()
    return "timeout" in error_str or "network error" in error_str

@retry(
    stop=stop_after_attempt(config.ANKICONNECT_MAX_RETRIES),
    wait=wait_fixed(config.ANKICONNECT_RETRY_DELAY),
    retry=retry_if_exception(is_retryable),
    reraise=True
)
def _ac_request(action, params=None, timeout=None):
    """
    Performs a request to AnkiConnect. Returns the 'result' on success.
    Raises AnkiConnectError on failure. Retries on timeout or network errors.
    """
    if timeout is None:
        timeout = config.ANKICONNECT_TIMEOUT
    
    try:
        payload = {
            "action": action,
            "version": 6,
            "params": params or {}
        }
        resp = requests.post(config.ANKICONNECT_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get("error") is not None:
            raise AnkiConnectError(data['error'])
        return data.get("result")
    except requests.exceptions.Timeout as e:
        raise AnkiConnectError(f"Network timeout communicating with AnkiConnect: {e}")
    except requests.exceptions.RequestException as e:
        raise AnkiConnectError(f"Network error communicating with AnkiConnect: {e}")


def _ensure_deck(deck_name: str):
    names = _ac_request("deckNames") or []
    if deck_name not in names:
        _ac_request("createDeck", {"deck": deck_name})


def _ensure_model():
    """
    Ensure the cloze model for sentence mining exists in Anki.
    """
    model_name = config.ANKI_MODEL_NAME
    names = _ac_request("modelNames") or []

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
        _ac_request("createModel", params)


def initialize_anki():
    """
    Checks connection to AnkiConnect and ensures deck and model exist.
    """
    try:
        _ac_request("version")
        deck_name = get_current_deck_name()
        _ensure_deck(deck_name)
        _ensure_model()
    except AnkiConnectError as e:
        # Catching the specific error after retries have failed.
        raise ConnectionError(f"AnkiConnect is not available: {e}")


def _remove_cloze_syntax(text):
    """Removes Anki cloze deletion syntax (e.g., {{c1::word}}) from a string."""
    if not text:
        return ""
    return re.sub(r'\{\{c\d+::(.*?)\}\}', r'\1', text)


def _create_cloze_sentence(word, sentence, cloze_number):
    """
    Creates a cloze-deleted sentence for a specific cloze number (c1, c2, etc.).
    """
    # Normalize hyphens for both word and sentence to ensure matching
    normalized_word = word.replace('‑', '-').replace('—', '-')
    normalized_sentence = sentence.replace('‑', '-').replace('—', '-')
    
    cloze_tag = f"{{{{c{cloze_number}::\\1}}}}"

    # First, try to replace the word if it's formatted as bold markdown
    pattern_bold = f'\\*\\*({re.escape(normalized_word)})\\*\\*'
    cloze_sentence, count = re.subn(pattern_bold, cloze_tag, normalized_sentence, flags=re.IGNORECASE)

    # If no bolded version was found, try replacing the plain word
    if count == 0:
        pattern_plain = f'({re.escape(normalized_word)})'
        cloze_sentence, count = re.subn(pattern_plain, cloze_tag, normalized_sentence, flags=re.IGNORECASE)

    # If regex methods failed, try the LLM
    if count == 0:
        print(f"Regex failed for '{word}'. Trying LLM to create cloze...")
        # Note: We need to adapt the LLM prompt if we want it to handle c1, c2 etc.
        # For now, we assume the LLM will use c1, and we replace it.
        llm_cloze = llm_service.create_cloze_with_llm(word, sentence)
        if '{{c1::' in llm_cloze:
            cloze_sentence = llm_cloze.replace('{{c1::', f'{{{{c{cloze_number}::')
        else:
             cloze_sentence = sentence # Fallback to sentence if LLM fails

    if f"c{cloze_number}::" not in cloze_sentence:
        raise ValueError(f"Failed to create a cloze for '{word}' in sentence: '{sentence}'")

    return cloze_sentence


def add_note(word, definition, sentence1, sentence2, context, tags=None):
    """
    Adds a single cloze note with two sentences to Anki.
    """
    clean_word = _remove_cloze_syntax(word)
    clean_context = _remove_cloze_syntax(context)
    deck_name = get_current_deck_name()
    model_name = config.ANKI_MODEL_NAME

    try:
        cloze1 = _create_cloze_sentence(word, sentence1, 1)
        cloze2 = _create_cloze_sentence(word, sentence2, 2)
    except ValueError as e:
        print(e)
        raise # Re-raise to be caught in main loop

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
        "options": {
            "allowDuplicate": True,
        },
        "tags": tags or [],
    }
    
    # Check for duplicates based on the 'Word' field before adding
    query = f'"deck:{deck_name}" "note:{model_name}" "Word:{clean_word}"'
    duplicate_notes = _ac_request("findNotes", {"query": query})
    if duplicate_notes:
        print(f"Note for '{word}' already exists. Skipping.")
        return

    try:
        _ac_request("addNote", {"note": note})
        print(f"Added note for '{word}'.")
    except AnkiConnectError as e:
        print(f"Failed to add note for '{word}': {e}")
        raise
