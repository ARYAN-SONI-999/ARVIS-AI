# ARVIS AI — Local Personal Assistant System

ARVIS is a premium, secure, and highly optimized local agentic AI assistant designed for Windows environments. It integrates advanced reasoning capabilities, a local settings UI, custom tool pipelines, and safety sandboxing constraints.

---

## 🚀 Features

### 1. Multi-Provider Cognitive Routing (Groq / Gemini / Claude / OpenRouter)
- **Primary Fast Inference**: Groq (utilizing key rotation & rate-limit fallback limits).
- **Secondary Reasoning**: OpenRouter fallback APIs.
- **Cognitive Reasoning**: Google Gemini & Anthropic Claude APIs.
- **Local LLM Execution**: Offline support via local Ollama endpoint (`http://localhost:11434/v1`).
- **Keyword-based Memory (RAG)**: Automatically searches past SQLite exchanges for matching terms and injects context dynamically into the model prompt.

### 2. Local Settings Dashboard UI
- Configure persona variables (`USER_NAME`, `AGENT_NAME`).
- Update API credentials (keys and model selections) securely.
- Configure local Ollama and SMTP email credentials.
- Auto-write adjustments to `.env` and load them live in-memory.
- **Clear logs feature**: Safely wipe sqlite database chat histories directly from the dashboard sidebar.

### 3. Integrated Tool Capabilities
- **File Management**: `list_files`, `create_file`, `read_file` (with line ranges), `delete_file`, `move_file`, `search_files`, `search_in_file`.
- **System Control**: WiFi/Bluetooth toggles, volume (mute/unmute), screen brightness, lock screen, shutdown/restart schedules.
- **Code Execution**: Run Python and JavaScript scripts locally.
- **SMTP Mail Sender**: Compose and send emails directly.
- **Desktop Control**: Manually capture screenshots, click coordinates, type text, or focus applications.
- **Voice System**: Low-latency Speech-to-Text and offline text-to-speech.

---

## 🛡️ Security & Sandbox Constraints

1. **Path Sandbox Bounds**: All file manager utilities are protected by strict path boundary validation checks in `skills/file_manager.py`. Any attempt to access paths outside the project workspace folder (via path traversals like `../` or absolute OS paths) throws a `PermissionError` and is blocked.
2. **AST Code safety check**: Python script executions are inspected using the Abstract Syntax Tree (`ast`) module before running. Imports of unauthorized modules (`os`, `sys`, `subprocess`, `shutil`, `socket`, `requests`, etc.) or use of `eval`/`exec` functions are automatically blocked.

---

## ⚙️ Configuration Setup

ARVIS loads configuration values from a [`.env`](.env) file:

```env
# Agent Personas
USER_NAME="Admin"
AGENT_NAME="ARVIS"

# AI Key Configurations
GROQ_API_KEY="gsk_your_groq_api_key_here"
GEMINI_API_KEY="your_gemini_api_key_here"
OPENROUTER_API_KEY="your_openrouter_api_key_here"
CLAUDE_API_KEY="your_claude_api_key_here"

# Local LLM Configurations
OLLAMA_HOST="http://localhost:11434"
OLLAMA_MODEL="llama3"
OLLAMA_PREFERRED="False"

# SMTP Email Configurations
EMAIL_ADDRESS="yourmail@gmail.com"
EMAIL_PASSWORD="xxxx xxxx xxxx xxxx"
```

---

## 🏃 Getting Started

### Prerequisites
- Python 3.10+ installed.
- Node.js (optional, for JavaScript execution).

### Installation & Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start ARVIS:
   ```bash
   run_arvis.bat
   ```
   This launches the Flask Web Dashboard on `http://127.0.0.1:5000` and automatically opens your browser.
3. Run verification tests:
   ```bash
   run_tests.bat
   ```
