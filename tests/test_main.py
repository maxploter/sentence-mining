import sys
from unittest.mock import MagicMock, call
import datetime

# Add the project root to the Python path
sys.path.insert(0, sys.path[0] + '/..')

from main import run_process
from todoist_service import TodoistService
from llm_service import LLMService
from anki_service import AnkiService

def test_end_to_end_flow(mocker):
    """
    End-to-end test for the main script, mocking the repository layer.
    """
    # 1. Mock Repositories (the external boundary of the app)
    mock_todoist_repo = MagicMock()
    mock_llm_repo = MagicMock()
    mock_anki_repo = MagicMock()

    # 2. Setup mock return values
    # Mock datetime to control the tags
    mock_fixed_datetime = datetime.datetime(2026, 1, 18)
    mocker.patch('main.datetime.datetime', MagicMock(now=MagicMock(return_value=mock_fixed_datetime)))

    # Mock Todoist tasks
    mock_task_1 = MagicMock()
    mock_task_1.id = '123'
    mock_task_1.content = 'test word'
    mock_task_1.description = 'This sentence contains the test word.'

    mock_task_2 = MagicMock()
    mock_task_2.id = '456'
    mock_task_2.content = 'english headspace'
    mock_task_2.description = 'So I’m checking my privilege here, acknowledging the fact that I’m living a very comfortable life if I have the headspace to muse about these matters.'

    mock_todoist_repo.get_project_tasks.return_value = [mock_task_1, mock_task_2]

    # Mock LLM calls
    mock_llm_repo.ask.side_effect=[
        'a word for testing', # definition for 'test word'
        'Another sentence with the test word.', # generated sentence
        'the mental space for something', # definition for 'headspace'
        'A generated sentence for headspace.' # generated sentence
    ]

    # Mock Anki calls
    mock_anki_repo.request.side_effect = lambda action, params=None: [] if action == 'findNotes' else None

    # 3. Instantiate REAL services with MOCK repositories
    llm_service = LLMService(mock_llm_repo)
    todoist_service = TodoistService(mock_todoist_repo)
    anki_service = AnkiService(mock_anki_repo, llm_service)

    # 4. Run the main application logic
    run_process(todoist_service, llm_service, anki_service)

    # 5. Assertions
    # Assert that the external-facing repositories were called correctly
    expected_tags = ['Year::2026', 'Month::01']
    
    # Verify Anki repository calls
    add_note_calls = mock_anki_repo.request.call_args_list
    added_notes = [
        c.args[1]['note'] for c in add_note_calls 
        if c.args[0] == 'addNote'
    ]
    assert len(added_notes) == 2

    note1 = next((n for n in added_notes if n['fields']['Word'] == 'test word'), None)
    assert note1 is not None
    assert note1['fields']['Text'] == 'This sentence contains the {{c1::test word}}.<br>Another sentence with the {{c2::test word}}.'

    note2 = next((n for n in added_notes if n['fields']['Word'] == 'headspace'), None)
    assert note2 is not None
    assert 'I have the {{c1::headspace}} to muse' in note2['fields']['Text']
    assert 'A generated sentence for {{c2::headspace}}.' in note2['fields']['Text']

    # Verify Todoist repository calls
    mock_todoist_repo.get_project_tasks.assert_called_once_with('english-words')
    complete_task_calls = [call('123'), call('456')]
    mock_todoist_repo.complete_task.assert_has_calls(complete_task_calls, any_order=True)
