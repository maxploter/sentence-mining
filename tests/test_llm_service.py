"""Tests for LLMService — definition prompt construction with per-language extras."""
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, sys.path[0] + "/..")

from llm_service import LLMService, get_definition_extras


@pytest.fixture
def mock_llm_repo():
    repo = MagicMock()
    repo.ask.return_value = "a test definition"
    return repo


@pytest.fixture
def service(mock_llm_repo):
    return LLMService(mock_llm_repo)


class TestGetDefinitionWithLearningLanguage:
    def test_english_learning_language_sends_no_extras_in_prompt(self, service, mock_llm_repo):
        """For English the prompt should be lean — no morphology block."""
        service.get_definition("run", "He runs every day.", instruction_language="english", learning_language="english")
        _, user_prompt = mock_llm_repo.ask.call_args[0]
        assert "nominative" not in user_prompt.lower()
        assert "ma-infinitive" not in user_prompt.lower()

    def test_estonian_learning_language_injects_verb_form_instructions(self, service, mock_llm_repo):
        """For Estonian the prompt must include ma- and da-infinitive guidance."""
        service.get_definition("tegema", "Ta teeb kodutöö.", instruction_language="english", learning_language="estonian")
        _, user_prompt = mock_llm_repo.ask.call_args[0]
        lower = user_prompt.lower()
        assert "ma" in lower
        assert "da" in lower

    def test_estonian_learning_language_injects_noun_form_instructions(self, service, mock_llm_repo):
        """For Estonian the prompt must include the four põhivormid for nouns."""
        service.get_definition("raamat", "Raamat on laual.", instruction_language="english", learning_language="estonian")
        _, user_prompt = mock_llm_repo.ask.call_args[0]
        lower = user_prompt.lower()
        assert "nominative" in lower
        assert "genitive" in lower
        assert "partitive" in lower

    def test_russian_learning_language_sends_no_extras_in_prompt(self, service, mock_llm_repo):
        """Russian has no extras yet — prompt should be plain."""
        service.get_definition("бежать", "Он бежит быстро.", instruction_language="english", learning_language="russian")
        _, user_prompt = mock_llm_repo.ask.call_args[0]
        assert "nominative" not in user_prompt.lower()
        assert "ma-infinitive" not in user_prompt.lower()

    def test_default_learning_language_is_english(self, service, mock_llm_repo):
        """Calling without learning_language should behave like english (no extras)."""
        service.get_definition("run", "He runs every day.", instruction_language="english")
        _, user_prompt = mock_llm_repo.ask.call_args[0]
        assert "nominative" not in user_prompt.lower()

    def test_definition_still_written_in_instruction_language(self, service, mock_llm_repo):
        """Regardless of learning language, instruction_language directive must remain."""
        service.get_definition("raamat", "Raamat on laual.", instruction_language="russian", learning_language="estonian")
        _, user_prompt = mock_llm_repo.ask.call_args[0]
        assert "russian" in user_prompt.lower()


class TestGetDefinitionExtras:
    def test_returns_empty_string_for_english(self):
        assert get_definition_extras("english") == ""

    def test_returns_empty_string_for_russian(self):
        assert get_definition_extras("russian") == ""

    def test_returns_non_empty_string_for_estonian(self):
        extras = get_definition_extras("estonian")
        assert extras != ""
        assert isinstance(extras, str)

    def test_estonian_extras_mentions_verb_and_ma_and_da(self):
        extras = get_definition_extras("estonian")
        lower = extras.lower()
        assert "verb" in lower
        assert "ma" in lower
        assert "da" in lower

    def test_estonian_extras_mentions_noun_and_four_forms(self):
        extras = get_definition_extras("estonian")
        lower = extras.lower()
        assert "noun" in lower
        assert "nominative" in lower
        assert "genitive" in lower
        assert "partitive" in lower

    def test_returns_empty_string_for_unknown_language(self):
        assert get_definition_extras("french") == ""

    def test_accepts_canonical_name_only(self):
        assert get_definition_extras("estonian") != ""
