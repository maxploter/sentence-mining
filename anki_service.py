import config
import random
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


def _create_cloze_sentence(word, sentence):
    """
    Creates a cloze-deleted sentence. First tries with regex, then falls back to LLM.
    """
    # Normalize hyphens for both word and sentence to ensure matching
    normalized_word = word.replace('‑', '-').replace('—', '-')
    normalized_sentence = sentence.replace('‑', '-').replace('—', '-')

    # First, try to replace the word if it's formatted as bold markdown
    pattern_bold = f'\\*\\*({re.escape(normalized_word)})\\*\\*'
    cloze_sentence, count = re.subn(pattern_bold, r'{{c1::\1}}', normalized_sentence, flags=re.IGNORECASE)

    # If no bolded version was found, try replacing the plain word
    if count == 0:
        pattern_plain = f'({re.escape(normalized_word)})'
        cloze_sentence, count = re.subn(pattern_plain, r'{{c1::\1}}', normalized_sentence, flags=re.IGNORECASE)

    # If regex methods failed, try the LLM
    if count == 0:
        print(f"Regex failed for '{word}'. Trying LLM to create cloze...")
        cloze_sentence = llm_service.create_cloze_with_llm(word, sentence)

    return cloze_sentence


def add_basic_note(word, definition, context, tags=None):
    """Adds a basic word/definition note to Anki."""
    clean_word = _remove_cloze_syntax(word)
    clean_context = _remove_cloze_syntax(context)
    deck_name = get_current_deck_name()
    model_name = getattr(config, "ANKI_MODEL_NAME_BASIC", f"{config.ANKI_MODEL_NAME} (Basic)")

    note = {
        "deckName": deck_name,
        "modelName": model_name,
        "fields": {
            "Word": clean_word,
            "Definition": definition,
            "Context": clean_context or "",
        },
        "options": {
            "allowDuplicate": False,
            "duplicateScope": "deck",
            "duplicateScopeOptions": {"deckName": deck_name, "checkChildren": True, "checkAllModels": False}
        },
        "tags": tags or [],
    }
    try:
        _ac_request("addNote", {"note": note})
        print(f"Added Basic note for '{word}'.")
    except AnkiConnectError as e:
        if "duplicate" in str(e):
            print(f"Basic note for '{word}' already exists. Resetting learning progress.")
            _handle_duplicate(clean_word)
        else:
            print(f"Failed to add Basic note for '{word}': {e}")
            raise

def add_cloze_note(word, sentences, context, all_words=None, tags=None):
    """
    Adds a cloze deletion note to Anki.
    Raises ValueError if a cloze cannot be created for any of the sentences.
    """
    clean_word = _remove_cloze_syntax(word)
    clean_context = _remove_cloze_syntax(context)
    deck_name = get_current_deck_name()
    model_name = getattr(config, "ANKI_MODEL_NAME_CLOZE", f"{config.ANKI_MODEL_NAME} (Cloze)")

    cloze_sentences = [_create_cloze_sentence(word, s) for s in sentences]

    # Check if at least one sentence has a cloze
    if not any('{{c1::' in s for s in cloze_sentences):
        raise ValueError(f"Failed to create a cloze for '{word}' in any of the provided sentences.")

    # Generate distractors for multiple choice
    distractors = []
    if all_words and len(all_words) > 1:
        potential_distractors = [w for w in all_words if w.lower() != word.lower()]
        num_to_sample = min(2, len(potential_distractors))
        if num_to_sample > 0:
            distractors = random.sample(potential_distractors, num_to_sample)
    
    placeholders = ['option2', 'option3']
    for i in range(2 - len(distractors)):
        distractors.append(placeholders[i])
    
    options_list = [word] + distractors
    random.shuffle(options_list)
    options = f"({', '.join(options_list)})"

    note = {
        "deckName": deck_name,
        "modelName": model_name,
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
            "duplicateScopeOptions": {"deckName": deck_name, "checkChildren": True, "checkAllModels": False}
        },
        "tags": tags or [],
    }
    try:
        _ac_request("addNote", {"note": note})
        print(f"Added Cloze note for '{word}'.")
    except AnkiConnectError as e:
        if "duplicate" in str(e):
             print(f"Cloze note for '{word}' already exists.")
        else:
            print(f"Failed to add Cloze note for '{word}': {e}")
            raise
