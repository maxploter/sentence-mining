import config
import random
import re
import requests
import datetime

# ---------------------------
# AnkiConnect helpers
# ---------------------------

def get_current_deck_name():
    now = datetime.datetime.now()
    return f"{config.ANKI_DECK_NAME}::{now.year}-{now.month:02}"

def _ac_request(action, params=None, timeout=10):
    """
    Performs a request to AnkiConnect. Returns the 'result' on success, None on failure.
    """
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
            raise RuntimeError(f"AnkiConnect error ({action}): {data.get('error')}")
        return data.get("result")
    except Exception as e:
        print(f"AnkiConnect request failed for action '{action}': {e}")
        return None


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
                    "Name": "Sentence Gap -> Word",
                    "Front": "{{cloze:Sentence1}}",
                    "Back": "{{cloze:Sentence1}}<br><br>{{Word}}<br><br>{{Context}}",
                },
                {
                    "Name": "Sentence Gap (Multiple Choice) -> Word",
                    "Front": "{{cloze:Sentence2}}<br><br>{{Options}}",
                    "Back": "{{cloze:Sentence2}}<br><br>{{Options}}<hr id=\"answer\">{{Word}}<br><br>{{Context}}",
                },
                {
                    "Name": "Sentence Gap 3 -> Word",
                    "Front": "{{cloze:Sentence3}}",
                    "Back": "{{cloze:Sentence3}}<br><br>{{Word}}<br><br>{{Context}}",
                },
            ],
        }
        _ac_request("createModel", params_cloze)


def initialize_anki():
    """
    Checks connection to AnkiConnect and ensures deck and models exist.
    """
    if _ac_request("version") is None:
        raise ConnectionError("AnkiConnect is not available. Please ensure Anki is running with AnkiConnect.")
    deck_name = get_current_deck_name()
    _ensure_deck(deck_name)
    _ensure_models()


def add_note(word, definition, sentences, context):
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

    # Placeholder for multiple choice options
    distractors = ['option2', 'option3']
    options_list = [word] + distractors
    random.shuffle(options_list)
    options = f"({', '.join(options_list)})"

    deck_name = get_current_deck_name()
    basic_model = getattr(config, "ANKI_MODEL_NAME_BASIC", f"{config.ANKI_MODEL_NAME} (Basic)")
    cloze_model = getattr(config, "ANKI_MODEL_NAME_CLOZE", f"{config.ANKI_MODEL_NAME} (Cloze)")

    basic_note = {
        "deckName": deck_name,
        "modelName": basic_model,
        "fields": {
            "Word": word,
            "Definition": definition,
            "Context": context or "",
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
            "Word": word,
            "Sentence1": cloze_sentences[0] if len(cloze_sentences) > 0 else '',
            "Sentence2": cloze_sentences[1] if len(cloze_sentences) > 1 else '',
            "Sentence3": cloze_sentences[2] if len(cloze_sentences) > 2 else '',
            "Context": context or "",
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

    # Try Basic then Cloze; only fall back if both fail
    basic_id = _ac_request("addNote", {"note": basic_note}, timeout=5)
    if basic_id:
        print(f"Added Basic note for '{word}' directly to Anki.")
    else:
        print(f"Failed to add Basic note via AnkiConnect for '{word}'.")

    cloze_id = _ac_request("addNote", {"note": cloze_note}, timeout=5)
    if cloze_id:
        print(f"Added Cloze note for '{word}' directly to Anki.")
    else:
        print(f"Failed to add Cloze note via AnkiConnect for '{word}'.")

    # Avoid creating local duplicates if at least one note was added
    if basic_id or cloze_id:
        return
