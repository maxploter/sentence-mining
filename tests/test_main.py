import sys
from unittest.mock import patch, MagicMock, call
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
    mock_add_basic_note = mocker.patch('anki_service.add_basic_note')
    mock_add_cloze_note = mocker.patch('anki_service.add_cloze_note')
    mock_complete_task = mocker.patch('todoist_service.complete_task')

    # Mock datetime to control the tags
    # Mock datetime to control the tags
    mock_fixed_datetime = datetime.datetime(2026, 1, 18)
    mocker.patch('main.datetime.datetime', MagicMock(now=MagicMock(return_value=mock_fixed_datetime)))

    # Mock Todoist task
    mock_task = MagicMock()
    mock_task.id = '123'
    mock_task.content = 'test word'
    mock_task.description = 'test context'
    mocker.patch('todoist_service.get_tasks', return_value=[mock_task])

    # Mock LLM calls
    mocker.patch('llm_service.get_definition', return_value='a word for testing')
    mocker.patch('llm_service.generate_sentences', return_value=['sentence 1', 'sentence 2', 'sentence 3'])
    mocker.patch('llm_service.strip_markdown_formatting', side_effect=lambda x: x)


    # 2. Run the main script
    main_module.main()

    # 3. Assertions
    # Verify that Anki notes were added correctly
    expected_tags = ['Year::2026', 'Month::01']
    
    mock_add_basic_note.assert_called_once_with(
        'test word', 
        'a word for testing', 
        'test context', 
        tags=expected_tags
    )
    
    mock_add_cloze_note.assert_called_once_with(
        'test word',
        ['sentence 1', 'sentence 2', 'sentence 3'],
        'test context',
        ['test word'],
        tags=expected_tags
    )

    # Verify that the Todoist task was completed
    mock_complete_task.assert_called_once_with('123')
