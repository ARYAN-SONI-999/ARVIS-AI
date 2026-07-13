from flask import Blueprint, render_template, jsonify, request
import os
import psutil
import platform
import getpass
import config
from agent.memory import ArvisMemory
from skills.computer_control import take_screenshot
from voice.voice_commands import VoicePipeline
import voice.tts_engine as tts

web_bp = Blueprint('web_bp', __name__)
memory = ArvisMemory()
voice_pipeline = None

@web_bp.route('/')
def index():
    return render_template('index.html', agent_name=config.AGENT_NAME, user_name=config.USER_NAME)

@web_bp.route('/dashboard')
def dashboard():
    """Renders the interactive AI dashboard."""
    # Trigger welcome greeting only when the dashboard page loads (skip on cloud)
    if os.environ.get("RENDER") != "true":
        tts.speak_async(f"Hello {config.USER_NAME}! I am {config.AGENT_NAME}, your AI assistant. All systems are online. How can I help you today?")
    return render_template('dashboard.html', agent_name=config.AGENT_NAME, user_name=config.USER_NAME)

@web_bp.route('/landing')
def landing():
    """Renders the futuristic product landing page."""
    return render_template('landing.html', agent_name=config.AGENT_NAME, user_name=config.USER_NAME)

@web_bp.route('/api/system/status', methods=['GET'])
def system_status():
    """Returns real-time system metrics as JSON for gauges."""
    try:
        cpu = psutil.cpu_percent(interval=None) # Non-blocking check
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        
        battery_pct = 100
        power_plugged = True
        if hasattr(psutil, "sensors_battery"):
            battery = psutil.sensors_battery()
            if battery:
                battery_pct = battery.percent
                power_plugged = battery.power_plugged

        status = {
            "cpu": cpu,
            "ram": memory.percent,
            "ram_used": memory.used // (1024**2),
            "ram_total": memory.total // (1024**2),
            "disk": disk.percent,
            "disk_free": disk.free // (1024**3),
            "battery": battery_pct,
            "power_plugged": power_plugged,
            "os": platform.system(),
            "user": getpass.getuser()
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@web_bp.route('/api/tasks/history', methods=['GET'])
def tasks_history():
    """Returns sqlite task run history."""
    tasks = memory.get_task_history(limit=50)
    return jsonify(tasks)

@web_bp.route('/api/screenshot/trigger', methods=['POST'])
def trigger_screenshot():
    """Directly triggers computer_control screenshot."""
    result = take_screenshot()
    return jsonify({"message": result})

@web_bp.route('/api/voice/toggle', methods=['POST'])
def toggle_voice():
    """Starts or stops the background voice wake word pipeline."""
    global voice_pipeline
    data = request.get_json() or {}
    enable = data.get("enable", False)
    
    if enable:
        if voice_pipeline is None or not voice_pipeline.is_alive():
            voice_pipeline = VoicePipeline()
            voice_pipeline.start()
            return jsonify({"status": "active", "message": "Voice listener activated."})
        else:
            return jsonify({"status": "active", "message": "Voice listener is already running."})
    else:
        if voice_pipeline and voice_pipeline.is_alive():
            voice_pipeline.stop()
            voice_pipeline.join(timeout=5)
            voice_pipeline = None
            return jsonify({"status": "inactive", "message": "Voice listener deactivated."})
        else:
            return jsonify({"status": "inactive", "message": "Voice listener is not running."})

@web_bp.route('/api/voice/status', methods=['GET'])
def get_voice_status():
    global voice_pipeline
    is_active = voice_pipeline is not None and voice_pipeline.is_alive()
    return jsonify({"status": "active" if is_active else "inactive"})

@web_bp.route('/settings')
def settings_page():
    """Renders the system settings page."""
    config_vars = {
        "USER_NAME": getattr(config, "USER_NAME", "User"),
        "AGENT_NAME": getattr(config, "AGENT_NAME", "ARVIS"),
        "GEMINI_API_KEY": getattr(config, "GEMINI_API_KEY", ""),
        "GEMINI_MODEL": getattr(config, "GEMINI_MODEL", "gemini-1.5-flash"),
        "GROQ_API_KEY": getattr(config, "GROQ_API_KEY", ""),
        "GROQ_MODEL": getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile"),
        "OPENROUTER_API_KEY": getattr(config, "OPENROUTER_API_KEY", ""),
        "OPENROUTER_MODEL": getattr(config, "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct"),
        "CLAUDE_API_KEY": os.getenv("CLAUDE_API_KEY", ""),
        "CLAUDE_MODEL": os.getenv("CLAUDE_MODEL", "claude-3-5-haiku-20241022"),
        "OLLAMA_HOST": getattr(config, "OLLAMA_HOST", "http://localhost:11434"),
        "OLLAMA_MODEL": getattr(config, "OLLAMA_MODEL", "llama3"),
        "OLLAMA_PREFERRED": getattr(config, "OLLAMA_PREFERRED", False),
        "EMAIL_ADDRESS": getattr(config, "EMAIL_ADDRESS", ""),
        "EMAIL_PASSWORD": getattr(config, "EMAIL_PASSWORD", "")
    }
    return render_template('settings.html', config_vars=config_vars)

@web_bp.route('/api/settings/save', methods=['POST'])
def save_settings():
    """Validates and updates settings in .env file and memory."""
    try:
        data = request.get_json() or {}
        env_path = os.path.join(config.BASE_DIR, ".env")
        
        # Read existing .env lines
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
        # Parse current key/values
        env_dict = {}
        for line in lines:
            line_str = line.strip()
            if "=" in line_str and not line_str.startswith("#"):
                k, v = line_str.split("=", 1)
                env_dict[k.strip()] = v.strip().strip('"').strip("'")
                
        # Apply updates
        for key, val in data.items():
            env_dict[key] = str(val)
            
        # Write back to .env
        with open(env_path, "w", encoding="utf-8") as f:
            for k, v in sorted(env_dict.items()):
                f.write(f'{k}="{v}"\n')
                
        # Load changes into memory
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)
        
        # Dynamically patch loaded config module attributes
        for key, val in data.items():
            setattr(config, key, val)
            if key == "OLLAMA_PREFERRED":
                # Handle bool type
                setattr(config, key, str(val).lower() in ("true", "1", "yes"))
                
        # Special sync for brain keys
        from agent.brain import ArvisBrain
        # To dynamically refresh active brain keys if they have been updated
        
        return jsonify({"success": True, "message": "Configurations saved successfully and applied."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@web_bp.route('/api/tasks/clear', methods=['POST'])
def clear_chat_history():
    """Deletes all tasks and conversation history from SQLite database."""
    try:
        conn = memory.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations")
        cursor.execute("DELETE FROM tasks")
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Chat history and task logs cleared successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@web_bp.route('/api/scheduler/list', methods=['GET'])
def get_scheduler_tasks():
    """Lists all active and completed scheduled tasks."""
    try:
        from skills.scheduler import load_scheduler_tasks
        tasks = load_scheduler_tasks()
        return jsonify(tasks)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@web_bp.route('/api/scheduler/delete', methods=['POST'])
def delete_scheduler_task():
    """Deletes a scheduled task by ID."""
    try:
        data = request.get_json() or {}
        task_id = data.get("id")
        if not task_id:
            return jsonify({"success": False, "message": "Task ID required."}), 400
            
        from skills.scheduler import load_scheduler_tasks, save_scheduler_tasks
        tasks = load_scheduler_tasks()
        
        # Filter task out
        filtered = [t for t in tasks if t.get("id") != task_id]
        if len(filtered) == len(tasks):
            return jsonify({"success": False, "message": f"Task ID '{task_id}' not found."}), 404
            
        save_scheduler_tasks(filtered)
        return jsonify({"success": True, "message": f"Scheduled task '{task_id}' cancelled successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
