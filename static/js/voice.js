class BrowserVoiceSTT {
    constructor(inputFieldId, micButtonId, onResultCallback) {
        this.inputField = document.getElementById(inputFieldId);
        this.micButton = document.getElementById(micButtonId);
        this.onResult = onResultCallback;
        this.recognition = null;
        this.isListening = false;
        
        this.initRecognition();
        this.bindEvents();
    }
    
    initRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn("Web Speech API is not supported in this browser. Voice dictation disabled.");
            this.micButton.style.display = 'none';
            return;
        }
        
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-US';
        
        this.recognition.onstart = () => {
            this.isListening = true;
            this.micButton.classList.add('mic-active');
            this.inputField.placeholder = "Listening... speak now.";
        };
        
        this.recognition.onerror = (e) => {
            console.error("Speech Recognition Error:", e);
            this.stopListening();
        };
        
        this.recognition.onend = () => {
            this.stopListening();
        };
        
        this.recognition.onresult = (e) => {
            const transcript = e.results[0][0].transcript;
            if (this.inputField) {
                this.inputField.value = transcript;
            }
            if (this.onResult) {
                this.onResult(transcript);
            }
        };
    }
    
    toggleListening() {
        if (!this.recognition) return;
        
        if (this.isListening) {
            this.recognition.stop();
        } else {
            this.recognition.start();
        }
    }
    
    stopListening() {
        this.isListening = false;
        if (this.micButton) {
            this.micButton.classList.remove('mic-active');
        }
        if (this.inputField) {
            this.inputField.placeholder = "Type your command here...";
        }
    }
    
    bindEvents() {
        if (this.micButton) {
            this.micButton.addEventListener('click', () => this.toggleListening());
        }
    }
}
