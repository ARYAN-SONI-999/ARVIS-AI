import threading
import time
import voice.stt_engine as stt
import voice.tts_engine as tts
from agent.brain import ArvisBrain
from agent.task_router import TaskRouter
import config

class VoicePipeline(threading.Thread):
    def __init__(self, session_id="voice_session"):
        super().__init__()
        self.session_id = session_id
        self.daemon = True
        self._stop_event = threading.Event()
        self.wake_words = [
            "arvis", "jarvis", "hey arvis", "hi arvis", "service", "harvest",
            "artist", "arrives", "iris", "elvis", "office", "avis", "harris", 
            "harves", "rvs", "alveoli", "jarves", "arbis", "orvis", "alvis"
        ]

    def run(self):
        self._stop_event.clear()
        router = TaskRouter()
        self.brain = ArvisBrain(session_id=self.session_id, task_router=router)
        print("🎙️ Background Voice Pipeline active...")
        # Calibrate microphone once at start to eliminate loop latency
        stt.calibrate(duration=1.5)

        while not self._stop_event.is_set():
            try:
                # Use a shorter timeout (2s) so the loop checks the stop event quickly
                text = stt.listen_once(timeout=2, phrase_time_limit=3)
                text_clean = text.lower().strip()
                if any(w in text_clean for w in self.wake_words):
                    print("🎙️ Wake word detected!")
                    
                    # Ascending high-pitch tones for wake confirmation
                    try:
                        import winsound
                        winsound.Beep(2000, 80)
                        winsound.Beep(2400, 120)
                    except Exception:
                        pass
                        
                    tts.speak("Yes? How can I help you?")
                    try:
                        command = stt.listen_once(timeout=6, phrase_time_limit=10)
                        print(f"🎙️ Command received: '{command}'")
                        
                        # Short acknowledgment chirp when starting computation
                        try:
                            import winsound
                            winsound.Beep(2200, 60)
                        except Exception:
                            pass
                            
                        final_reply = ""
                        for update in self.brain.execute_react_loop(command):
                            if update["type"] == "final_answer":
                                final_reply = update["content"]
                                break
                            elif update["type"] == "error":
                                final_reply = f"Error: {update['message']}"
                                break
                        if final_reply:
                            tts.speak(final_reply)
                        else:
                            tts.speak("Action completed.")
                    except Exception as cmd_err:
                        print(f"Command error: {cmd_err}")
                        
                        # Descending lower-pitch tones for errors/timeout
                        try:
                            import winsound
                            winsound.Beep(1600, 120)
                            winsound.Beep(1200, 150)
                        except Exception:
                            pass
                            
                        tts.speak("Sorry, I didn't catch that.")
            except Exception:
                pass  # timeout or no audio — keep looping

    def stop(self):
        self._stop_event.set()
