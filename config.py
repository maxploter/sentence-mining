import os
from dotenv import load_dotenv

load_dotenv()

# Secrets (loaded from .env file)
TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")

# Configuration (can be changed here)
TODOIST_PROJECT_NAME = "english-words"
ANKI_DECK_NAME = "english::sentence-mining"
ANKI_MODEL_NAME = "English Vocabulary Model"

# Derived model names for AnkiConnect mode (you can override with env if desired)
ANKI_MODEL_NAME_BASIC = os.getenv("ANKI_MODEL_NAME_BASIC", f"{ANKI_MODEL_NAME} (Basic)")
ANKI_MODEL_NAME_CLOZE = os.getenv("ANKI_MODEL_NAME_CLOZE", f"{ANKI_MODEL_NAME} (Cloze)")

# AnkiConnect integration
ANKICONNECT_URL = os.getenv("ANKICONNECT_URL", "http://localhost:8765")

# AnkiConnect retry settings
ANKICONNECT_TIMEOUT = int(os.getenv("ANKICONNECT_TIMEOUT", "20"))
ANKICONNECT_MAX_RETRIES = int(os.getenv("ANKICONNECT_MAX_RETRIES", "3"))
ANKICONNECT_RETRY_DELAY = int(os.getenv("ANKICONNECT_RETRY_DELAY", "3"))