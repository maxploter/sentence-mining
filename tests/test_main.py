import sys
from unittest.mock import MagicMock, call
import datetime

# Add the project root to the Python path
sys.path.insert(0, sys.path[0] + '/..')

import main as main_module

def test_end_to_end_flow(mocker):
    """
    End-to-end test for the main script, mocking all external services.
    """
    # 1. Mock external services
    mocker.patch('anki_service.initialize_anki')
    # Mock the lowest-level AnkiConnect request function
    mock_ac_request = mocker.patch('anki_service._ac_request')
    # Make the findNotes action return no duplicates
    mock_ac_request.side_effect = lambda action, params: [] if action == 'findNotes' else None

    mock_complete_task = mocker.patch('todoist_service.complete_task')

    # Mock datetime to control the tags
    mock_fixed_datetime = datetime.datetime(2026, 1, 18)
    mocker.patch('main.datetime.datetime', MagicMock(now=MagicMock(return_value=mock_fixed_datetime)))

    # Mock Todoist tasks (ensure words are in sentences for regex to work)
    mock_task_1 = MagicMock()
    mock_task_1.id = '123'
    mock_task_1.content = 'test word'
    mock_task_1.description = 'This sentence contains the test word.'

    mock_task_2 = MagicMock()
    mock_task_2.id = '456'
    mock_task_2.content = 'english headspace'
    mock_task_2.description = 'So I’m checking my privilege here, acknowledging the fact that I’m living a very comfortable life if I have the headspace to muse about these matters.'

    mocker.patch('todoist_service.get_tasks', return_value=[mock_task_1, mock_task_2])

    # Mock LLM calls
    mocker.patch('llm_service.get_definition', side_effect=['a word for testing', 'the mental space for something'])
    mocker.patch('llm_service.generate_sentence', side_effect=['Another sentence with the test word.', 'A generated sentence for headspace.'])
    mocker.patch('llm_service.strip_markdown_formatting', side_effect=lambda x: x)


    # 2. Run the main script
    main_module.main()

    # 3. Assertions
    expected_tags = ['Year::2026', 'Month::01']
    
    # Verify that the 'addNote' action was called with the correct cloze format
    add_note_calls = mock_ac_request.call_args_list
    
    # Filter for the 'addNote' calls
    added_notes = [
        c.args[1]['note'] for c in add_note_calls 
        if c.args[0] == 'addNote'
    ]

    assert len(added_notes) == 2

    # Check note 1 for 'test word'
    note1 = next((n for n in added_notes if n['fields']['Word'] == 'test word'), None)
    assert note1 is not None
    assert note1['fields']['Text'] == 'This sentence contains the {{c1::test word}}.<br>Another sentence with the {{c2::test word}}.'
    assert note1['fields']['Definition'] == 'a word for testing'
    assert note1['fields']['Context'] == 'test word'
    assert note1['tags'] == expected_tags

    # Check note 2 for 'headspace'
    note2 = next((n for n in added_notes if n['fields']['Word'] == 'headspace'), None)
    assert note2 is not None
    assert 'I have the {{c1::headspace}} to muse' in note2['fields']['Text']
    assert 'A generated sentence for {{c2::headspace}}.' in note2['fields']['Text']
    assert note2['fields']['Definition'] == 'the mental space for something'
    assert note2['fields']['Context'] == 'english headspace'
    assert note2['tags'] == expected_tags


    # Verify that the Todoist tasks were completed
    complete_task_calls = [call('123'), call('456')]
    mock_complete_task.assert_has_calls(complete_task_calls, any_order=True)
