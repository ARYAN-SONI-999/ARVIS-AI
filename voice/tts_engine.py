import os
import time
import threading
import uuid
import ctypes
from gtts import gTTS
import pyttsx3
import config

import re

class TTSEngine:
    def __init__(self):
        self.offline_engine = None
        self.lock = threading.Lock()
        self._thread_local = threading.local()

    def _get_offline_engine(self):
        if not hasattr(self._thread_local, 'engine'):
            if os.environ.get("RENDER") == "true":
                self._thread_local.engine = None
                return None
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', config.VOICE_SPEED)
                engine.setProperty('volume', config.VOICE_VOLUME)
                
                # Try setting to a female/male voice if available
                voices = engine.getProperty('voices')
                if len(voices) > 1:
                    engine.setProperty('voice', voices[1].id)
                self._thread_local.engine = engine
            except Exception as e:
                print(f"Warning: Failed to initialize pyttsx3 engine: {e}")
                self._thread_local.engine = None
        return self._thread_local.engine

    def init_offline_engine(self):
        """Initializes the pyttsx3 engine on-demand (to prevent blocking threads on startup)."""
        if self.offline_engine is None:
            self.offline_engine = self._get_offline_engine()

    def speak_offline(self, text):
        """Offline speech fallback using pyttsx3."""
        engine = self._get_offline_engine()
        if engine:
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                print(f"Offline speech error: {e}")
        else:
            print(f"TTS offline unavailable. Log: {text}")

    def play_audio_windows(self, file_path):
        """Plays an MP3 file natively on Windows using MCI windll commands without any external dependencies."""
        try:
            abs_path = os.path.abspath(file_path)
            
            # Close any previous alias just in case
            ctypes.windll.winmm.mciSendStringW("close arvis_mp3", None, 0, 0)
            
            # Open command
            open_cmd = f'open "{abs_path}" type mpegvideo alias arvis_mp3'
            ret = ctypes.windll.winmm.mciSendStringW(open_cmd, None, 0, 0)
            if ret != 0:
                print(f"MCI open error code: {ret}")
                return False
                
            # Play command
            ret = ctypes.windll.winmm.mciSendStringW("play arvis_mp3", None, 0, 0)
            if ret != 0:
                print(f"MCI play error code: {ret}")
                return False
                
            # Wait until playback is done
            status_buf = ctypes.create_unicode_buffer(64)
            while True:
                ctypes.windll.winmm.mciSendStringW("status arvis_mp3 mode", status_buf, 64, 0)
                if status_buf.value != "playing":
                    break
                time.sleep(0.1)
                
            # Close alias
            ctypes.windll.winmm.mciSendStringW("close arvis_mp3", None, 0, 0)
            return True
        except Exception as e:
            print(f"Native audio playback failed: {e}")
            return False

    def clean_text(self, text):
        """Strips markdown formatting, link URLs, code blocks, bullet points, and emojis from text for a clean spoken output."""
        if not text:
            return ""
            
        # 1. Remove code blocks entirely
        text = re.sub(r'```[\s\S]*?```', '', text)
        
        # 2. Replace markdown links [text](url) with just 'text'
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # 3. Remove inline code backticks
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # 4. Remove bold/italic markup: **, *, __, _
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        
        # 5. Remove headers: #, ##, ### at start of lines
        text = re.sub(r'(?m)^#+\s+', '', text)
        
        # 6. Remove bullet/number list prefixes at start of lines
        text = re.sub(r'(?m)^[-*+]\s+', '', text)
        text = re.sub(r'(?m)^\d+\.\s+', '', text)
        
        # 7. Strip emojis, miscellaneous symbols, and variation selectors
        text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        text = re.sub(r'[\u2600-\u27bf]', '', text)
        text = re.sub(r'[\ufe00-\ufe0f]', '', text)
        
        # 8. Clean up extra newlines and spaces
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def speak(self, text):
        """Synchronously speaks text, using gTTS if online, falling back to pyttsx3."""
        cleaned_text = self.clean_text(text)
        if not cleaned_text:
            return
            
        with self.lock:
            # Create a unique audio file name to avoid Windows file sharing lock conflicts
            audio_id = str(uuid.uuid4())[:8]
            temp_file = os.path.join(config.AUDIO_DIR, f"speech_{audio_id}.mp3")
            
            success = False
            try:
                # Online TTS using gTTS
                tts = gTTS(text=cleaned_text, lang='en', slow=False)
                tts.save(temp_file)
                
                # Play using native Windows MCI player
                success = self.play_audio_windows(temp_file)
                
                # Cleanup temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
            except Exception as e:
                print(f"Online TTS failed, falling back to offline speech: {e}")
                
            if not success:
                # Cleanup if file was left over
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
                # Run offline TTS
                self.speak_offline(cleaned_text)

    def speak_async(self, text):
        """Speaks text in a background thread to prevent UI freezing."""
        thread = threading.Thread(target=self.speak, args=(text,), daemon=True)
        thread.start()
        return thread
        
# Global engine instance
_tts_engine = TTSEngine()

def speak(text):
    _tts_engine.speak(text)

def speak_async(text):
    _tts_engine.speak_async(text)

