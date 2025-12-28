import genanki
import config
import random
import re
import requests

# Module-level local fallback (used when AnkiConnect is unavailable mid-run)
_LOCAL_MODEL_BASIC = None
_LOCAL_MODEL_CLOZE = None
_LOCAL_DECK = None

# ---------------------------
# AnkiConnect helpers
# ---------------------------

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


def _ac_available():
    """
    Returns True if AnkiConnect is enabled in config and reachable.
    """
    if not getattr(config, "USE_ANKICONNECT", False):
        return False
    version = _ac_request("version")
    return version is not None


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


def _get_or_create_local_models_and_deck():
    """
    Lazily create local genanki models (Basic + Cloze) and deck for fallback when AnkiConnect becomes unavailable mid-run.
    """
    global _LOCAL_MODEL_BASIC, _LOCAL_MODEL_CLOZE, _LOCAL_DECK

    if _LOCAL_MODEL_BASIC is None:
        _LOCAL_MODEL_BASIC = genanki.Model(
            1607392319,  # Model ID, should be unique
            getattr(config, "ANKI_MODEL_NAME_BASIC", f"{config.ANKI_MODEL_NAME} (Basic)"),
            fields=[
                {'name': 'Word'},
                {'name': 'Definition'},
                {'name': 'Context'},
            ],
            templates=[
                {
                    'name': 'Word -> Definition',
                    'qfmt': '{{Word}}',
                    'afmt': '{{FrontSide}}<hr id="answer">{{Definition}}<br><br>{{Context}}',
                },
                {
                    'name': 'Definition -> Word',
                    'qfmt': '{{Definition}}',
                    'afmt': '{{FrontSide}}<hr id="answer">{{Word}}<br><br>{{Context}}',
                },
            ],
            css="""
            .card {
             font-family: arial;
             font-size: 20px;
             text-align: center;
             color: black;
             background-color: white;
            }
            """
        )

    if _LOCAL_MODEL_CLOZE is None:
        _LOCAL_MODEL_CLOZE = genanki.Model(
            1607392320,  # Different unique Model ID
            getattr(config, "ANKI_MODEL_NAME_CLOZE", f"{config.ANKI_MODEL_NAME} (Cloze)"),
            fields=[
                {'name': 'Sentence1'},
                {'name': 'Sentence2'},
                {'name': 'Sentence3'},
                {'name': 'Word'},
                {'name': 'Context'},
                {'name': 'Options'},  # For multiple choice
            ],
            templates=[
                {
                    'name': 'Sentence Gap -> Word',
                    'qfmt': '{{cloze:Sentence1}}',
                    'afmt': '{{cloze:Sentence1}}<br><br>{{Word}}<br><br>{{Context}}',
                },
                {
                    'name': 'Sentence Gap (Multiple Choice) -> Word',
                    'qfmt': '{{cloze:Sentence2}}<br><br>{{Options}}',
                    'afmt': '{{cloze:Sentence2}}<br><br>{{Options}}<hr id="answer">{{Word}}<br><br>{{Context}}',
                },
                {
                    'name': 'Sentence Gap 3 -> Word',
                    'qfmt': '{{cloze:Sentence3}}',
                    'afmt': '{{cloze:Sentence3}}<br><br>{{Word}}<br><br>{{Context}}',
                },
            ],
            css="""
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
            """,
            model_type=genanki.Model.CLOZE
        )

    if _LOCAL_DECK is None:
        _LOCAL_DECK = genanki.Deck(
            2059400110,  # Deck ID, should be unique
            config.ANKI_DECK_NAME
        )

    return _LOCAL_MODEL_BASIC, _LOCAL_MODEL_CLOZE, _LOCAL_DECK


# Anki model for vocabulary cards (genanki fallback)
def create_anki_model():
    """
    When AnkiConnect is available, ensure the remote deck and models exist and return None.
    Otherwise, ensure local Basic + Cloze models exist for .apkg generation and return the Basic model.
    """
    if _ac_available():
        _ensure_deck(config.ANKI_DECK_NAME)
        _ensure_models()
        return None

    # Prepare local fallback models and deck
    local_basic_model, _, _ = _get_or_create_local_models_and_deck()
    return local_basic_model


def create_anki_deck(model):
    """Creates an Anki deck for genanki fallback. No-op for AnkiConnect mode."""
    if _ac_available():
        return None

    return genanki.Deck(
        2059400110,  # Deck ID, should be unique
        config.ANKI_DECK_NAME
    )


def add_note(deck, model, word, definition, sentences, context):
    """Adds a note either directly to Anki (AnkiConnect) or to the local genanki deck."""

    # For cloze deletion, replace the word with {{c1::word}}
    cloze_sentences = []
    for i, sentence in enumerate(sentences):
        # Use re.sub for case-insensitive replacement
        cloze_sentence = re.sub(f'({re.escape(word)})', r'{{c1::\1}}', sentence, flags=re.IGNORECASE)
        cloze_sentences.append(cloze_sentence)

    # Placeholder for multiple choice options
    distractors = ['option2', 'option3']
    options_list = [word] + distractors
    random.shuffle(options_list)
    options = f"({', '.join(options_list)})"

    # If AnkiConnect is available, push directly (two notes: Basic and Cloze)
    if _ac_available():
        basic_model = getattr(config, "ANKI_MODEL_NAME_BASIC", f"{config.ANKI_MODEL_NAME} (Basic)")
        cloze_model = getattr(config, "ANKI_MODEL_NAME_CLOZE", f"{config.ANKI_MODEL_NAME} (Cloze)")

        basic_note = {
            "deckName": config.ANKI_DECK_NAME,
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
                    "deckName": config.ANKI_DECK_NAME,
                    "checkChildren": True,
                    "checkAllModels": False
                }
            }
        }
        cloze_note = {
            "deckName": config.ANKI_DECK_NAME,
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
                    "deckName": config.ANKI_DECK_NAME,
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

    # Fallback: add to genanki deck (for later .apkg export)
    if deck is None or model is None:
        # Lazily create local deck/models if not provided or if AnkiConnect became unavailable
        local_basic_model, local_cloze_model, deck = _get_or_create_local_models_and_deck()
    else:
        # Even if a model/deck were passed, ensure we can create both Basic and Cloze locally
        local_basic_model, local_cloze_model, deck = _get_or_create_local_models_and_deck()

    # Add Basic note
    basic_note = genanki.Note(
        model=local_basic_model,
        fields=[
            word,
            definition,
            context or ""
        ]
    )
    deck.add_note(basic_note)

    # Add Cloze note (Cloze model; cloze fields first)
    cloze_note = genanki.Note(
        model=local_cloze_model,
        fields=[
            cloze_sentences[0] if len(cloze_sentences) > 0 else '',
            cloze_sentences[1] if len(cloze_sentences) > 1 else '',
            cloze_sentences[2] if len(cloze_sentences) > 2 else '',
            word,
            context or "",
            options
        ]
    )
    deck.add_note(cloze_note)


def save_deck(deck):
    """Saves the deck to an .apkg file when using genanki; no-op if using AnkiConnect."""
    if _ac_available():
        print("Notes added directly to Anki via AnkiConnect. Skipping .apkg export.")
        return

    # If deck passed in is None, try module-level fallback (when AnkiConnect failed mid-run)
    global _LOCAL_DECK
    if deck is None:
        deck = _LOCAL_DECK

    if deck is None:
        print("No local deck to save. Nothing to export.")
        return

    package = genanki.Package(deck)
    package.write_to_file(f'{config.ANKI_DECK_NAME}.apkg')
    print(f"Deck saved to {config.ANKI_DECK_NAME}.apkg")
