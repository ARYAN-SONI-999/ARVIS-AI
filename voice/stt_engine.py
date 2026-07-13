import sys

# PyAudio fallback alias for Python 3.14 on Windows
try:
    import pyaudio
except ImportError:
    try:
        import pyaudiowpatch as pyaudio
        sys.modules['pyaudio'] = pyaudio
    except ImportError:
        pass

import speech_recognition as sr

class STTEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Set dynamic energy threshold adjustments
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8         # Faster recognition endpoint detection (default is 1.0)
        self.recognizer.non_speaking_duration = 0.5    # Reduce post-phrase silence record duration
        self.recognizer.operation_timeout = 10         # Google API network call timeout limit
        self.calibrated = False
        
    def calibrate(self, duration=1.5):
        """Calibrates microphone once to filter background noise."""
        if not self.calibrated:
            try:
                with sr.Microphone() as source:
                    print("🎙️ STT Engine: Calibrating for ambient noise...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=duration)
                    self.calibrated = True
                    print(f"🎙️ Calibration complete. Energy threshold set to: {self.recognizer.energy_threshold:.2f}")
            except Exception as e:
                print(f"⚠️ Calibration failed: {e}. Using default threshold.")
        
    def listen_once(self, timeout=5, phrase_time_limit=10):
        """Listens to the microphone and transcribes the speech.
        
        Returns the transcription string or raises an exception.
        """
        try:
            # Lazy calibration check
            if not self.calibrated:
                self.calibrate(duration=1.0)
                
            with sr.Microphone() as source:
                print("🎙️ Listening...")
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
                
            print("🎙️ Transcribing...")
            # Use Google Speech Recognition (free api wrapper) with US-English locale for higher accuracy
            text = self.recognizer.recognize_google(audio, language="en-US")
            return text
        except sr.WaitTimeoutError:
            raise Exception("Timeout: No speech detected.")
        except sr.UnknownValueError:
            raise Exception("Speech not understood.")
        except sr.RequestError as e:
            raise Exception(f"Network error from Google Speech Recognition service: {e}")
        except OSError as e:
            raise Exception(f"Microphone or sound card issue: {e}")
        except Exception as e:
            raise Exception(f"Speech recognition failed: {e}")
            
# Global instance
_stt_engine = STTEngine()

def listen_once(timeout=5, phrase_time_limit=10):
    return _stt_engine.listen_once(timeout, phrase_time_limit)

def calibrate(duration=1.5):
    return _stt_engine.calibrate(duration)
