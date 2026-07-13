import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Primary AI Model - Groq & OpenRouter Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")

# Default smart models for high-quality reasoning, debugging and citation
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Ollama Local LLM Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_PREFERRED = os.getenv("OLLAMA_PREFERRED", "False").lower() in ("true", "1", "yes")

# User Configurations
USER_NAME = os.getenv("USER_NAME", "User")
AGENT_NAME = os.getenv("AGENT_NAME", "ARVIS")

# Email configurations
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

# Voice Engine Settings
VOICE_SPEED = 175
VOICE_VOLUME = 0.9

# Flask & Web Configurations
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecretkey_arvis")
PORT = int(os.getenv("PORT", 5000))
DEBUG = False
AUTO_OPEN_BROWSER = True

# Directory Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "arvis.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
CODE_RUNS_DIR = os.path.join(TEMP_DIR, "code_runs")
AUDIO_DIR = os.path.join(TEMP_DIR, "audio")

# Create required directories on import
for directory in [LOGS_DIR, TEMP_DIR, CODE_RUNS_DIR, AUDIO_DIR, os.path.join(BASE_DIR, "database")]:
    os.makedirs(directory, exist_ok=True)
