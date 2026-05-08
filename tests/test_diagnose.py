import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import diagnose

def test_print_section():
    with patch('builtins.print') as mock_print:
        diagnose.print_section("Test Title")
        assert mock_print.call_count == 3
        mock_print.assert_any_call("\n" + "="*70)
        mock_print.assert_any_call("  Test Title")
        mock_print.assert_any_call("="*70)

def test_check_imports_success():
    with patch('builtins.__import__', return_value=MagicMock()) as mock_import, \
         patch('builtins.print') as mock_print:
        diagnose.check_imports()
        assert mock_import.call_count == 7 # For each module
        assert mock_print.call_count > 0

def test_check_imports_failure():
    # We only want to mock __import__ for the specific modules in check_imports
    original_import = __import__
    
    def side_effect(name, *args, **kwargs):
        modules = ['pyttsx3', 'edge_tts', 'elevenlabs', 'pygame', 'simpleaudio', 'winsound', 'requests']
        if name in modules:
            raise ImportError(f"mocked import error for {name}")
        return original_import(name, *args, **kwargs)
        
    with patch('builtins.__import__', side_effect=side_effect), \
         patch('builtins.print') as mock_print:
        diagnose.check_imports()
        assert mock_print.call_count > 0

@patch('os.path.exists', return_value=True)
@patch('dotenv.load_dotenv')
def test_check_env_exists(mock_load_dotenv, mock_exists):
    with patch('builtins.print') as mock_print:
        with patch('jarvis_core.config.TTS_BACKEND', 'pyttsx3', create=True), \
             patch('jarvis_core.config.TTS_VOICE', 'test_voice', create=True), \
             patch('jarvis_core.config.ELEVENLABS_API_KEY', 'test_key', create=True), \
             patch('jarvis_core.config.ELEVENLABS_VOICE', 'test_eleven_voice', create=True):
            diagnose.check_env()
            assert mock_exists.called
            assert mock_load_dotenv.called
            assert mock_print.call_count > 0

@patch('os.path.exists', return_value=False)
def test_check_env_not_exists(mock_exists):
    with patch('builtins.print') as mock_print:
        diagnose.check_env()
        assert mock_exists.called
        assert mock_print.call_count > 0

@patch('pyttsx3.init')
def test_test_pyttsx3_success(mock_init):
    mock_engine = MagicMock()
    mock_init.return_value = mock_engine
    
    mock_voice = MagicMock()
    mock_voice.name = "Test Voice"
    mock_engine.getProperty.return_value = [mock_voice]
    
    with patch('builtins.print') as mock_print:
        diagnose.test_pyttsx3()
        mock_init.assert_called_once()
        mock_engine.getProperty.assert_called_with('voices')
        mock_engine.setProperty.assert_called_with('rate', 175)
        mock_engine.say.assert_called_with("Hello from pyttsx3")
        mock_engine.runAndWait.assert_called_once()
        assert mock_print.call_count > 0

@patch('pyttsx3.init', side_effect=Exception("mocked init error"))
def test_test_pyttsx3_failure(mock_init):
    with patch('builtins.print') as mock_print:
        diagnose.test_pyttsx3()
        mock_init.assert_called_once()
        assert mock_print.call_count > 0

@patch('jarvis_core.core.speak.Speaker')
def test_test_speaker_class_success(mock_speaker_class):
    mock_speaker = MagicMock()
    mock_speaker.backend = 'offline'
    mock_speaker_class.return_value = mock_speaker
    
    with patch('builtins.print') as mock_print:
        diagnose.test_speaker_class()
        mock_speaker_class.assert_called_once_with(offline=True)
        mock_speaker.speak_output.assert_called_once_with("Testing Jarvis speaker class")
        assert mock_print.call_count > 0

@patch('jarvis_core.core.speak.Speaker', side_effect=Exception("mocked speaker error"))
def test_test_speaker_class_failure(mock_speaker_class):
    with patch('builtins.print') as mock_print:
        diagnose.test_speaker_class()
        mock_speaker_class.assert_called_once_with(offline=True)
        assert mock_print.call_count > 0

@patch('jarvis_core.core.speak.Speaker')
@patch('jarvis_core.brain.llm_client.Brain')
def test_test_full_pipeline_success(mock_brain_class, mock_speaker_class):
    mock_speaker = MagicMock()
    mock_speaker_class.return_value = mock_speaker
    
    mock_brain = MagicMock()
    mock_brain.think.return_value = "Paris"
    mock_brain_class.return_value = mock_brain
    
    with patch('builtins.print') as mock_print:
        diagnose.test_full_pipeline()
        mock_speaker_class.assert_called_once_with(offline=True)
        mock_brain_class.assert_called_once_with(model="llama3.2")
        mock_brain.think.assert_called_once_with("What is the capital of France?")
        mock_speaker.speak_output.assert_called_once_with("Paris")
        assert mock_print.call_count > 0

@patch('jarvis_core.core.speak.Speaker')
@patch('jarvis_core.brain.llm_client.Brain', side_effect=Exception("mocked brain error"))
def test_test_full_pipeline_brain_failure(mock_brain_class, mock_speaker_class):
    mock_speaker = MagicMock()
    mock_speaker_class.return_value = mock_speaker
    
    with patch('builtins.print') as mock_print:
        diagnose.test_full_pipeline()
        mock_speaker_class.assert_called_once_with(offline=True)
        mock_brain_class.assert_called_once_with(model="llama3.2")
        # speaker should still be tested if brain fails
        mock_speaker.speak_output.assert_called_once_with("This is a test of the speaker system")
        assert mock_print.call_count > 0
