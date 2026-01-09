import config
import random
import re
import requests
import datetime
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception

class AnkiConnectError(Exception):
    """Custom exception for AnkiConnect errors."""
    pass

# ---------------------------
# AnkiConnect helpers
# ---------------------------

def get_current_deck_name():
    now = datetime.datetime.now()
    return f"{config.ANKI_DECK_NAME}::{now.year}-{now.month:02}"

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


def _ensure_models():
    """
    Ensure two models in Anki:
    - Basic model for Word<->Definition cards (non-cloze)
    - Cloze model for sentence cloze cards
    """
    basic_name = getattr(config, "ANKI_MODEL_NAME_BASIC", f"{config.ANKI_MODEL_NAME} (Basic)")
    cloze_name = getattr(config, "ANKI_MODEL_NAME_CLOZE", f"{config.ANKI_MODEL_NAME} (Cloze)")

    names = _ac_request("modelNames") or []

    css_basic = """
    .card {
     font-family: arial;
     font-size: 20px;
     text-align: center;
     color: black;
     background-color: white;
    }
    """

    css_cloze = """
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

    if basic_name not in names:
        params_basic = {
            "modelName": basic_name,
            "inOrderFields": [
                "Word",
                "Definition",
                "Context",
            ],
            "css": css_basic,
            "isCloze": False,
            "cardTemplates": [
                {
                    "Name": "Word -> Definition",
                    "Front": "{{Word}}",
                    "Back": "{{FrontSide}}<hr id=\"answer\">{{Definition}}<br><br>{{Context}}",
                },
                {
                    "Name": "Definition -> Word",
                    "Front": "{{Definition}}",
                    "Back": "{{FrontSide}}<hr id=\"answer\">{{Word}}<br><br>{{Context}}",
                },
            ],
        }
        _ac_request("createModel", params_basic)

    # Refresh names after create
    names = _ac_request("modelNames") or []

    if cloze_name not in names:
        params_cloze = {
            "modelName": cloze_name,
            "inOrderFields": [
                "Word",
                "Sentence1",
                "Sentence2",
                "Sentence3",
                "Context",
                "Options",
            ],
            "css": css_cloze,
            "isCloze": True,
            "cardTemplates": [
                {
                    "Name": "Sentence 1 (Cloze)",
                    "Front": "{{cloze:Sentence1}}",
                    "Back": "{{cloze:Sentence1}}<br><br>{{Word}}<br><br>{{Context}}",
                },
                {
                    "Name": "Sentence 1 (Multiple Choice)",
                    "Front": "{{cloze:Sentence1}}<br><br>{{Options}}",
                    "Back": "{{cloze:Sentence1}}<br><br>{{Options}}<hr id=\"answer\">{{Word}}<br><br>{{Context}}",
                },
                {
                    "Name": "Sentence 2 (Cloze)",
                    "Front": "{{cloze:Sentence2}}",
                    "Back": "{{cloze:Sentence2}}<br><br>{{Word}}<br><br>{{Context}}",
                },
                {
                    "Name": "Sentence 2 (Multiple Choice)",
                    "Front": "{{cloze:Sentence2}}<br><br>{{Options}}",
                    "Back": "{{cloze:Sentence2}}<br><br>{{Options}}<hr id=\"answer\">{{Word}}<br><br>{{Context}}",
                },
                {
                    "Name": "Sentence 3 (Cloze)",
                    "Front": "{{cloze:Sentence3}}",
                    "Back": "{{cloze:Sentence3}}<br><br>{{Word}}<br><br>{{Context}}",
                },
                {
                    "Name": "Sentence 3 (Multiple Choice)",
                    "Front": "{{cloze:Sentence3}}<br><br>{{Options}}",
                    "Back": "{{cloze:Sentence3}}<br><br>{{Options}}<hr id=\"answer\">{{Word}}<br><br>{{Context}}",
                },
            ],
        }
        _ac_request("createModel", params_cloze)


def initialize_anki():
    """
    Checks connection to AnkiConnect and ensures deck and models exist.
    """
    try:
        _ac_request("version")
        deck_name = get_current_deck_name()
        _ensure_deck(deck_name)
        _ensure_models()
    except AnkiConnectError as e:
        # Catching the specific error after retries have failed.
        raise ConnectionError(f"AnkiConnect is not available: {e}")


def _remove_cloze_syntax(text):
    """Removes Anki cloze deletion syntax (e.g., {{c1::word}}) from a string."""
    if not text:
        return ""
    return re.sub(r'\{\{c\d+::(.*?)\}\}', r'\1', text)


def _handle_duplicate(word):
    """Finds a note by word and resets its learning progress."""
    deck_name = get_current_deck_name()
    query = f'"deck:{deck_name}" "Word:{word}"'
    try:
        note_ids = _ac_request("findNotes", {"query": query})
        if not note_ids:
            print(f"Could not find duplicate note for word '{word}' to forget.")
            return

        print(f"Found {len(note_ids)} duplicate notes for '{word}'.")

        notes_info = _ac_request("notesInfo", {"notes": note_ids})
        card_ids = []
        for note_info in notes_info:
            card_ids.extend(note_info['cards'])
        
        if card_ids:
            _ac_request("forgetCards", {"cards": card_ids})
            print(f"Reset learning progress for {len(card_ids)} cards of word '{word}'.")

    except AnkiConnectError as e:
        print(f"Error handling duplicate for '{word}': {e}")


def add_note(word, definition, sentences, context, all_words=None):
    """Adds a note either directly to Anki (AnkiConnect) or to the local genanki deck."""

    # For cloze deletion, replace the word with {{c1::word}}
    cloze_sentences = []
    for sentence in sentences:
        # Normalize hyphens for both word and sentence to ensure matching
        normalized_word = word.replace('‑', '-').replace('—', '-')
        normalized_sentence = sentence.replace('‑', '-').replace('—', '-')

        # First, try to replace the word if it's formatted as bold markdown
        pattern_bold = f'\\*\\*({re.escape(normalized_word)})\\*\\*'
        cloze_sentence, count = re.subn(pattern_bold, r'{{c1::\1}}', normalized_sentence, flags=re.IGNORECASE)

        # If no bolded version was found, try replacing the plain word
        if count == 0:
            pattern_plain = f'({re.escape(normalized_word)})'
            cloze_sentence, _ = re.subn(pattern_plain, r'{{c1::\1}}', normalized_sentence, flags=re.IGNORECASE)

        cloze_sentences.append(cloze_sentence)

    # Generate distractors for multiple choice
    distractors = []
    if all_words and len(all_words) > 1:
        potential_distractors = [w for w in all_words if w.lower() != word.lower()]
        num_to_sample = min(2, len(potential_distractors))
        if num_to_sample > 0:
            distractors = random.sample(potential_distractors, num_to_sample)

    # Fallback to placeholder distractors if not enough were found
    placeholders = ['option2', 'option3']
    for i in range(2 - len(distractors)):
        distractors.append(placeholders[i])

    options_list = [word] + distractors
    random.shuffle(options_list)
    options = f"({', '.join(options_list)})"

    # Clean the word and context from any accidental cloze syntax before using in non-cloze fields
    clean_word = _remove_cloze_syntax(word)
    clean_context = _remove_cloze_syntax(context)

    deck_name = get_current_deck_name()
    basic_model = getattr(config, "ANKI_MODEL_NAME_BASIC", f"{config.ANKI_MODEL_NAME} (Basic)")
    cloze_model = getattr(config, "ANKI_MODEL_NAME_CLOZE", f"{config.ANKI_MODEL_NAME} (Cloze)")

    basic_note = {
        "deckName": deck_name,
        "modelName": basic_model,
        "fields": {
            "Word": clean_word,
            "Definition": definition,
            "Context": clean_context or "",
        },
        "options": {
            "allowDuplicate": False,
            "duplicateScope": "deck",
            "duplicateScopeOptions": {
                "deckName": deck_name,
                "checkChildren": True,
                "checkAllModels": False
            }
        }
    }
    cloze_note = {
        "deckName": deck_name,
        "modelName": cloze_model,
        "fields": {
            "Word": clean_word,
            "Sentence1": cloze_sentences[0] if len(cloze_sentences) > 0 else '',
            "Sentence2": cloze_sentences[1] if len(cloze_sentences) > 1 else '',
            "Sentence3": cloze_sentences[2] if len(cloze_sentences) > 2 else '',
            "Context": clean_context or "",
            "Options": options,
        },
        "options": {
            "allowDuplicate": False,
            "duplicateScope": "deck",
            "duplicateScopeOptions": {
                "deckName": deck_name,
                "checkChildren": True,
                "checkAllModels": False
            }
        }
    }

    # Try to add the basic note
    try:
        _ac_request("addNote", {"note": basic_note})
        print(f"Added Basic note for '{word}' directly to Anki.")
    except AnkiConnectError as e:
        if "duplicate" in str(e):
            print(f"Note for '{word}' already exists. Resetting learning progress.")
            _handle_duplicate(clean_word)
        else:
            print(f"Failed to add Basic note for '{word}': {e}")

    # Try to add the cloze note
    try:
        _ac_request("addNote", {"note": cloze_note})
        print(f"Added Cloze note for '{word}' directly to Anki.")
    except AnkiConnectError as e:
        if "duplicate" in str(e):
            # The duplicate handler would have already been called for the basic note,
            # so we can just log this or do nothing.
            pass
        else:
            print(f"Failed to add Cloze note for '{word}': {e}")
