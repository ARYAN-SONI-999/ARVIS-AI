import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add root folder to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from voice.tts_engine import TTSEngine

class TestVoice(unittest.TestCase):
    @patch('voice.tts_engine.gTTS')
    @patch('voice.tts_engine.ctypes.windll.winmm')
    def test_tts_online_flow(self, mock_winmm, mock_gTTS):
        # Mock successful online TTS saving and playing
        mock_winmm.mciSendStringW.return_value = 0 # success code
        
        tts = TTSEngine()
        # Should not raise exception
        tts.speak("Testing online voice outputs.")
        
        # Verify gTTS was called and ctypes mci commands executed
        mock_gTTS.assert_called_once()
        mock_winmm.mciSendStringW.assert_called()

    @patch('voice.tts_engine.pyttsx3')
    @patch('voice.tts_engine.gTTS')
    def test_tts_offline_fallback(self, mock_gTTS, mock_pyttsx3):
        # Force online flow to raise Exception
        mock_gTTS.side_effect = Exception("No internet connection")
        
        mock_engine = MagicMock()
        mock_pyttsx3.init.return_value = mock_engine
        
        tts = TTSEngine()
        tts.speak("Testing offline voice fallback.")
        
        # Verify fallback pyttsx3 engine initialized and spoke
        mock_pyttsx3.init.assert_called_once()
        mock_engine.say.assert_called_once_with("Testing offline voice fallback.")
        mock_engine.runAndWait.assert_called_once()

if __name__ == "__main__":
    unittest.main()
