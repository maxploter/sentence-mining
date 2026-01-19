import sys
from unittest.mock import MagicMock, call
import datetime
import argparse # Import argparse

# Add the project root to the Python path
sys.path.insert(0, sys.path[0] + '/..')

from main import run_process, main as main_func # Rename main to main_func to avoid conflict
from llm_service import LLMService
from anki_service import AnkiService
from word_processor import WordProcessor 
from domain.models import SourceSentence
from domain.task_completion_handler import TaskCompletionHandler 


def test_end_to_end_flow(mocker):
    """
    End-to-end test for the main script, mocking the repository and data source layers.
    """
    # 0. Mock argparse for main function
    mock_args = MagicMock()
    mock_args.source = 'todoist' # Test with todoist source by default
    mock_args.csv_file = 'words.csv' 
    mock_args.text_file = 'sentences.txt' # Default value for new text_file source
    mocker.patch('argparse.ArgumentParser.parse_args', return_value=mock_args)

    # 1. Mock Repositories (the external boundary of the app)
    mock_llm_repo = MagicMock()
    mock_anki_repo = MagicMock()
    mock_todoist_repo = MagicMock() # Need this now for TodoistSentenceSource and TodoistTaskCompletionHandler

    # 2. Mock Data Source and Task Completion Handler
    mock_sentence_source = MagicMock()
    mock_task_completion_handler = MagicMock(spec=TaskCompletionHandler) # Mock an instance of the ABC

    # 3. Setup mock return values
    # Mock datetime to control the tags
    mock_fixed_datetime = datetime.datetime(2026, 1, 18)
    mocker.patch('main.datetime.datetime', MagicMock(now=MagicMock(return_value=mock_fixed_datetime)))

    # Mock SourceSentence items returned by the data source
    mock_mined_sentence_1 = SourceSentence(
        id='123',
        entry_text='test word',
        sentence='This sentence contains the test word.'
    )

    mock_mined_sentence_2 = SourceSentence(
        id='456',
        entry_text='english headspace',
        sentence='So I’m checking my privilege here, acknowledging the fact that I’m living a very comfortable life if I have the headspace to muse about these matters.'
    )
    mock_sentence_source.fetch_sentences.return_value = [mock_mined_sentence_1, mock_mined_sentence_2]

    # Mock LLM calls
    mock_llm_repo.ask.side_effect=[
        'a word for testing', # definition for 'test word'
        'Another sentence with the test word.', # generated sentence
        'the mental space for something', # definition for 'headspace'
        'A generated sentence for headspace.' # generated sentence
    ]

    # Mock Anki calls (for findNotes and addNote)
    mock_anki_repo.request.side_effect = lambda action, params=None: [] if action == 'findNotes' else None

    # 4. Instantiate REAL services with MOCK repositories and data source
    word_processor = WordProcessor() # WordProcessor is a pure class, no need to mock
    llm_service = LLMService(mock_llm_repo)
    anki_service = AnkiService(mock_anki_repo, llm_service) # AnkiService needs LLMService

    # 5. Run the main application logic - we now mock the components main_func creates
    # and call main_func directly.
    mocker.patch('main.TodoistRepository', return_value=mock_todoist_repo)
    mocker.patch('main.LLMRepository', return_value=mock_llm_repo)
    mocker.patch('main.AnkiRepository', return_value=mock_anki_repo)
    # Patch the data source and task completion handler that main_func will create
    mocker.patch('main.TodoistSentenceSource', return_value=mock_sentence_source)
    mocker.patch('main.TodoistTaskCompletionHandler', return_value=mock_task_completion_handler)
    # Patch CsvSentenceSource and NoOpTaskCompletionHandler in case args.source is 'csv' or 'text_file'
    mocker.patch('main.CsvSentenceSource', return_value=MagicMock())
    mocker.patch('main.TextFileSentenceSource', return_value=MagicMock()) # New TextFileSentenceSource
    mocker.patch('main.NoOpTaskCompletionHandler', return_value=MagicMock()) # NoOp for CSV/TextFile

    main_func() # Call the main function directly

    # 6. Assertions
    # Assert that the external-facing repositories and handlers were called correctly
    expected_tags = ['Year::2026', 'Month::01']
    
    # Verify Anki repository calls
    add_note_calls = [
        c.args[1]['note'] for c in mock_anki_repo.request.call_args_list 
        if c.args[0] == 'addNote'
    ]
    assert len(add_note_calls) == 2

    note1 = next((n for n in add_note_calls if n['fields']['Word'] == 'test word'), None)
    assert note1 is not None
    assert note1['fields']['Text'] == 'This sentence contains the {{c1::test word}}.<br>Another sentence with the {{c2::test word}}.'
    assert note1['fields']['Definition'] == 'a word for testing'
    assert note1['fields']['Context'] == 'test word'
    assert note1['tags'] == expected_tags

    note2 = next((n for n in add_note_calls if n['fields']['Word'] == 'headspace'), None)
    assert note2 is not None
    assert 'I have the {{c1::headspace}} to muse' in note2['fields']['Text']
    assert 'A generated sentence for {{c2::headspace}}.' in note2['fields']['Text']
    assert note2['fields']['Definition'] == 'the mental space for something'
    assert note2['fields']['Context'] == 'english headspace'
    assert note2['tags'] == expected_tags

    # Verify LLM repository calls (get_definition and generate_sentence)
    expected_llm_ask_calls = [
        # Definition for 'test word'
        call(
            'You are a helpful assistant that provides concise definitions.',
            '\n        Please provide a concise definition for the word or phrase "test word".\n        The word appeared in the following context:\n        ---\n        This sentence contains the test word.\n        ---\n        Based on this context, what is the most likely meaning of "test word"?\n        Provide only the definition, without any extra text or explanations.\n        '
        ),
        # Generated sentence for 'test word'
        call(
            'You are a helpful assistant that generates an example sentence.',
            '\n        The word is "test word".\n        Its definition is: "a word for testing".\n        It appeared in the original context: "This sentence contains the test word.".\n\n        Please generate one new, distinct sentence using the word "test word".\n        The sentence should be easy to understand and a.\n        Return only the sentence.\n        '
        ),
        # Definition for 'headspace'
        call(
            'You are a helpful assistant that provides concise definitions.',
            '\n        Please provide a concise definition for the word or phrase "headspace".\n        The word appeared in the following context:\n        ---\n        So I’m checking my privilege here, acknowledging the fact that I’m living a very comfortable life if I have the headspace to muse about these matters.\n        ---\n        Based on this context, what is the most likely meaning of "headspace"?\n        Provide only the definition, without any extra text or explanations.\n        '
        ),
        # Generated sentence for 'headspace'
        call(
            'You are a helpful assistant that generates an example sentence.',
            '\n        The word is "headspace".\n        Its definition is: "the mental space for something".\n        It appeared in the original context: "So I’m checking my privilege here, acknowledging the fact that I’m living a very comfortable life if I have the headspace to muse about these matters.".\n\n        Please generate one new, distinct sentence using the word "headspace".\n        The sentence should be easy to understand and a.\n        Return only the sentence.\n        '
        ),
    ]
    mock_llm_repo.ask.assert_has_calls(expected_llm_ask_calls, any_order=True)

    # Verify SentenceSource was called
    mock_sentence_source.fetch_sentences.assert_called_once()

    # Verify TaskCompletionHandler calls
    complete_task_calls = [call('123'), call('456')]
    mock_task_completion_handler.complete_task.assert_has_calls(complete_task_calls, any_order=True)

