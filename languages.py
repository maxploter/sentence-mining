"""
Language normalization: maps ISO 639-1 codes and long names to canonical long names.
Extend _LANGUAGE_MAP to add more languages.
"""

_LANGUAGE_MAP: dict[str, str] = {
    # English
    "en": "english",
    "english": "english",
    # Estonian (ISO 639-1: et)
    "et": "estonian",
    "estonian": "estonian",
    # Russian
    "ru": "russian",
    "russian": "russian",
}

DEFAULT_LEARNING_LANGUAGE = "english"
DEFAULT_INSTRUCTION_LANGUAGE = "english"


def normalize_language(value: str) -> str:
    """
    Normalizes a language code or long name to a canonical lowercase long name.

    Accepted forms (case-insensitive):
        English:  en, english
        Estonian: et, estonian
        Russian:  ru, russian

    Raises ValueError for unrecognized values.
    """
    key = value.strip().lower()
    canonical = _LANGUAGE_MAP.get(key)
    if canonical is None:
        supported_names = sorted(set(_LANGUAGE_MAP.values()))
        supported_codes = sorted(k for k, v in _LANGUAGE_MAP.items() if k != v)
        raise ValueError(
            f"Unknown language '{value}'. "
            f"Supported names: {', '.join(supported_names)}. "
            f"Short ISO codes: {', '.join(supported_codes)}."
        )
    return canonical
