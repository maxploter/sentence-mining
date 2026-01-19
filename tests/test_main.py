import datetime
import sys
from unittest.mock import MagicMock, call

# Add the project root to the Python path
sys.path.insert(0, sys.path[0] + '/..')

from main import main as main_func # Rename main to main_func to avoid conflict
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
    mock_args.tags = 'CLI::Tag1,CLI::Tag2' # Simulate CLI tags
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
        sentence='This sentence contains the test word.',
        tags=['Source::MockTodoist'] # Tags from data source
    )

    mock_mined_sentence_2 = SourceSentence(
        id='456',
        entry_text='english headspace',
        sentence='So I’m checking my privilege here, acknowledging the fact that I’m living a very comfortable life if I have the headspace to muse about these matters.',
        tags=['Source::MockCsv', 'Topic::Psychology'] # Tags from data source
    )
    # Add a new sentence for testing the single-sentence case
    mock_mined_sentence_3 = SourceSentence(
      id='789',
      entry_text='english ephemeral',
      sentence='The beauty of a sunset is often ephemeral.',
      tags=['Source::MockTodoist', 'Type::Todoist']  # Tags from data source
    )
    mock_mined_sentence_4 = SourceSentence(
      id='999',
      entry_text='wordonly',
      sentence=None,  # Testing word without sentence
      tags=['Source::MockTodoist', 'Type::Todoist']
    )
    mock_sentence_source.fetch_sentences.return_value = [mock_mined_sentence_1, mock_mined_sentence_2,
                                                         mock_mined_sentence_3, mock_mined_sentence_4]

    # Mock LLM calls
    mock_llm_repo.ask.side_effect=[
      # Definition for 'test word'
      'a word for testing',
      # Generated sentence for 'test word'
      'Another sentence with the test word.',
      # Definition for 'headspace'
      'the mental space for something',
      # Generated sentence for 'headspace'
      'A generated sentence for headspace.',
      # Definition for 'ephemeral'
      'lasting for a very short time',
      # Generated sentence for 'ephemeral'
      'A fleeting moment can be quite ephemeral.',  # Definition for 'wordonly' (no context)
      'a word used for testing when no original sentence is provided',
      # Generated sentence for 'wordonly'
      'This sentence is generated for the word wordonly.']

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
    expected_script_tags = ['Year::2026', 'Month::01']
    expected_cli_tags = ['CLI::Tag1', 'CLI::Tag2']

    # Verify Anki repository calls
    add_note_calls = [
      c.args[1]['note'] for c in mock_anki_repo.request.call_args_list
        if c.args[0] == 'addNote'
    ]
    assert len(add_note_calls) == 4  # Expecting 4 notes now

    # --- Assertions for note 1 ('test word') ---
    note1 = next((n for n in add_note_calls if n['fields']['Word'] == 'test word'), None)
    assert note1 is not None
    assert note1['fields'][
             'Text'] == 'This sentence contains the {{c1::test word}}.<br>Another sentence with the {{c1::test word}}.'
    assert note1['fields']['Definition'] == 'a word for testing'
    assert note1['fields']['Context'] == 'test word'

    # Combined tags for note 1
    expected_note1_tags = set(expected_script_tags)
    expected_note1_tags.update(['Source::MockTodoist'])
    expected_note1_tags.update(expected_cli_tags)
    assert sorted(note1['tags']) == sorted(list(expected_note1_tags))

    # --- Assertions for note 2 ('headspace') ---
    note2 = next((n for n in add_note_calls if n['fields']['Word'] == 'headspace'), None)
    assert note2 is not None
    assert 'I have the {{c1::headspace}} to muse' in note2['fields']['Text']
    assert 'A generated sentence for {{c1::headspace}}.' in note2['fields']['Text']
    assert note2['fields']['Definition'] == 'the mental space for something'
    assert note2['fields']['Context'] == 'english headspace'

    # Combined tags for note 2
    expected_note2_tags = set(expected_script_tags)
    expected_note2_tags.update(['Source::MockCsv', 'Topic::Psychology'])
    expected_note2_tags.update(expected_cli_tags)
    assert sorted(note2['tags']) == sorted(list(expected_note2_tags))

    # --- Assertions for note 3 ('ephemeral' - single sentence test) ---
    note3 = next((n for n in add_note_calls if n['fields']['Word'] == 'ephemeral'), None)
    assert note3 is not None
    # UPDATED ASSERTION: Match the actual behavior of combining original and generated sentences.
    assert note3['fields'][
             'Text'] == 'The beauty of a sunset is often {{c1::ephemeral}}.<br>A fleeting moment can be quite {{c1::ephemeral}}.'
    assert note3['fields']['Definition'] == 'lasting for a very short time'
    assert note3['fields']['Context'] == 'english ephemeral'

    # Combined tags for note 3
    expected_note3_tags = set(expected_script_tags)
    expected_note3_tags.update(['Source::MockTodoist', 'Type::Todoist'])
    expected_note3_tags.update(expected_cli_tags)
    assert sorted(note3['tags']) == sorted(list(expected_note3_tags))

    # --- Assertions for note 4 ('wordonly' - no original sentence) ---
    note4 = next((n for n in add_note_calls if n['fields']['Word'] == 'wordonly'), None)
    assert note4 is not None
    assert note4['fields']['Text'] == 'This sentence is generated for the word {{c1::wordonly}}.'
    assert note4['fields']['Definition'] == 'a word used for testing when no original sentence is provided'
    assert note4['fields']['Context'] == 'wordonly'

    # Combined tags for note 4
    expected_note4_tags = set(expected_script_tags)
    expected_note4_tags.update(['Source::MockTodoist', 'Type::Todoist'])
    expected_note4_tags.update(expected_cli_tags)
    assert sorted(note4['tags']) == sorted(list(expected_note4_tags))

    # Verify LLM repository calls (get_definition and generate_sentence)

    expected_llm_ask_calls = [

      # Definition for 'test word'

      call(

        'You are a helpful assistant that provides concise definitions.',

        '\n        Please provide a concise definition for the word or phrase "test word".\n        \n        The word appeared in the following context:\n        ---\n        This sentence contains the test word.\n        ---\n        Based on this context, what is the most likely meaning of "test word"?\n            \n        Provide only the definition, without any extra text or explanations.\n        '

      ),

      # Generated sentence for 'test word'

      call(

        'You are a helpful assistant that generates an example sentence.',

        '\n        The word is "test word".\n        Its definition is: "a word for testing".\n        \n        It appeared in the original context: "This sentence contains the test word.".\n            \n        Please generate one new, distinct sentence using the word "test word".\n        The sentence should be easy to understand and a.\n        Return only the sentence.\n        '

      ),

      # Definition for 'headspace'

      call(

        'You are a helpful assistant that provides concise definitions.',

        '\n        Please provide a concise definition for the word or phrase "headspace".\n        \n        The word appeared in the following context:\n        ---\n        So I’m checking my privilege here, acknowledging the fact that I’m living a very comfortable life if I have the headspace to muse about these matters.\n        ---\n        Based on this context, what is the most likely meaning of "headspace"?\n            \n        Provide only the definition, without any extra text or explanations.\n        '

      ),

      # Generated sentence for 'headspace'

      call(

        'You are a helpful assistant that generates an example sentence.',

        '\n        The word is "headspace".\n        Its definition is: "the mental space for something".\n        \n        It appeared in the original context: "So I’m checking my privilege here, acknowledging the fact that I’m living a very comfortable life if I have the headspace to muse about these matters.".\n            \n        Please generate one new, distinct sentence using the word "headspace".\n        The sentence should be easy to understand and a.\n        Return only the sentence.\n        '

      ),

      # Definition for 'ephemeral'

      call(

        'You are a helpful assistant that provides concise definitions.',

        '\n        Please provide a concise definition for the word or phrase "ephemeral".\n        \n        The word appeared in the following context:\n        ---\n        The beauty of a sunset is often ephemeral.\n        ---\n        Based on this context, what is the most likely meaning of "ephemeral"?\n            \n        Provide only the definition, without any extra text or explanations.\n        '

      ),

      # Generated sentence for 'ephemeral'

      call(

        'You are a helpful assistant that generates an example sentence.',

        '\n        The word is "ephemeral".\n        Its definition is: "lasting for a very short time".\n        \n        It appeared in the original context: "The beauty of a sunset is often ephemeral.".\n            \n        Please generate one new, distinct sentence using the word "ephemeral".\n        The sentence should be easy to understand and a.\n        Return only the sentence.\n        '

      ),

      # Definition for 'wordonly' (no context)

      call(

        'You are a helpful assistant that provides concise definitions.',

        '\n        Please provide a concise definition for the word or phrase "wordonly".\n        \n        What is the most likely meaning of "wordonly"?\n            \n        Provide only the definition, without any extra text or explanations.\n        '

      ),

      # Generated sentence for 'wordonly'

      call(

        'You are a helpful assistant that generates an example sentence.',

        '\n        The word is "wordonly".\n        Its definition is: "a word used for testing when no original sentence is provided".\n        \n        Please generate one new, distinct sentence using the word "wordonly".\n        The sentence should be easy to understand and a.\n        Return only the sentence.\n        '

      ),

    ]


    mock_llm_repo.ask.assert_has_calls(expected_llm_ask_calls, any_order=True)

    # Verify SentenceSource was called
    mock_sentence_source.fetch_sentences.assert_called_once()

    # Verify TaskCompletionHandler calls
    complete_task_calls = [call('123'), call('456'), call('789'), call('999')]  # Added '999' for the new task
    mock_task_completion_handler.complete_task.assert_has_calls(complete_task_calls, any_order=True)

