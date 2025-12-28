import os
from dotenv import load_dotenv

load_dotenv()

# Secrets (loaded from .env file)
TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")

# Configuration (can be changed here)
TODOIST_PROJECT_NAME = "english-words"
ANKI_DECK_NAME = "English Vocabulary Request"
ANKI_MODEL_NAME = "English Vocabulary Model"

# Derived model names for AnkiConnect mode (you can override with env if desired)
ANKI_MODEL_NAME_BASIC = os.getenv("ANKI_MODEL_NAME_BASIC", f"{ANKI_MODEL_NAME} (Basic)")
ANKI_MODEL_NAME_CLOZE = os.getenv("ANKI_MODEL_NAME_CLOZE", f"{ANKI_MODEL_NAME} (Cloze)")

# AnkiConnect integration
# Enable to add notes directly to Anki via the AnkiConnect add-on.
USE_ANKICONNECT = os.getenv("ANKICONNECT_ENABLE", "false").strip().lower() in ("1", "true", "yes", "on")
ANKICONNECT_URL = os.getenv("ANKICONNECT_URL", "http://localhost:8765")