import os
import sys

IS_RENDER = os.environ.get("RENDER") == "true"

# Disable eventlet's green DNS patching to prevent import deadlock on Python 3.12+ / 3.14+
os.environ['EVENTLET_NO_GREENDNS'] = 'yes'

# Force UTF-8 encoding for standard streams to prevent UnicodeEncodeError in Windows CMD
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

import eventlet
eventlet.monkey_patch()
import time
import datetime
import threading
import webbrowser
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

# Add script folder to python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
from web.routes import web_bp
from web.socket_handler import register_socket_events
from agent.memory import ArvisMemory
from agent.brain import ArvisBrain
from agent.task_router import TaskRouter
from skills.scheduler import load_scheduler_tasks, save_scheduler_tasks
import voice.tts_engine as tts
from concurrent.futures import ThreadPoolExecutor

scheduler_executor = ThreadPoolExecutor(max_workers=4)

# Initialize Flask Application
app = Flask(__name__)
app.config['SECRET_KEY'] = config.FLASK_SECRET_KEY
CORS(app)

# Register Blueprint
app.register_blueprint(web_bp)

# Initialize SocketIO with eventlet support for async duplex streaming
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
register_socket_events(socketio)

# Background scheduler thread
def scheduler_loop():
    print("⏰ Background scheduler thread running.")
    router = TaskRouter()
    
    while True:
        # Sleep for 60 seconds between checks
        time.sleep(60)
        
        tasks = load_scheduler_tasks()
        if not tasks:
            continue
            
        now = datetime.datetime.now()
        now_hm = now.strftime("%H:%M")
        now_ymd_hm = now.strftime("%Y-%m-%d %H:%M")
        
        updated = False
        for task in tasks:
            if task.get("status") == "completed":
                continue
                
            schedule_type = task.get("schedule")
            scheduled_time = task.get("time")
            task_id = task.get("id")
            prompt = task.get("prompt")
            
            run_needed = False
            if schedule_type == "once":
                if now_ymd_hm >= scheduled_time and not task.get("last_run"):
                    run_needed = True
            elif schedule_type == "daily":
                if now_hm >= scheduled_time:
                    # Check if run today
                    last_run_str = task.get("last_run")
                    if not last_run_str:
                        run_needed = True
                    else:
                        last_run_date = datetime.datetime.fromisoformat(last_run_str).date()
                        if last_run_date < now.date():
                            run_needed = True
            elif schedule_type == "hourly":
                # Check minutes match
                sched_min = scheduled_time.split(":")[-1]
                if now.strftime("%M") == sched_min:
                    last_run_str = task.get("last_run")
                    if not last_run_str:
                        run_needed = True
                    else:
                        last_run = datetime.datetime.fromisoformat(last_run_str)
                        if (now - last_run).total_seconds() >= 3590:
                            run_needed = True
                            
            if run_needed:
                print(f"⏰ [Scheduler]: Executing scheduled task '{prompt}' (ID: {task_id})...")
                task["last_run"] = now.isoformat()
                if schedule_type == "once":
                    task["status"] = "completed"
                updated = True
                
                # Execute in background thread
                def run_scheduled_prompt(pr, tid):
                    try:
                        brain = ArvisBrain(session_id=f"scheduled_{tid}", task_router=router)
                        for update in brain.execute_react_loop(pr):
                            if update["type"] == "final_answer":
                                print(f"⏰ [Scheduler ID {tid} Completed]: {update['content']}")
                                # Speak notification
                                tts.speak_async(f"Scheduled task run complete. {update['content'][:60]}")
                                break
                    except Exception as err:
                        print(f"⏰ [Scheduler Error]: {err}")
                        
                scheduler_executor.submit(run_scheduled_prompt, prompt, task_id)
                
        if updated:
            save_scheduler_tasks(tasks)

def replace_jarvis_with_arvis():
    import re
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    exclude_dirs = {".git", "venv", "__pycache__", "temp", "logs", "static/assets", ".agents", "brain"}
    
    replacements = {
        r"\bJARVIS\b": "ARVIS",
        r"\bjarvis\b": "arvis",
        r"\bJarvis\b": "Arvis"
    }
    
    for root, dirs, files in os.walk(workspace_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith((".py", ".html", ".js", ".css", ".txt", ".md", ".json", ".bat", ".sh")):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    new_content = content
                    for pattern, repl in replacements.items():
                        new_content = re.sub(pattern, repl, new_content)
                    
                    if new_content != content:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(f"🔄 [ARVIS Startup]: Replaced JARVIS references in {file}")
                except Exception:
                    pass

# Web app execution point
def main():
    # 0. Automatically replace remaining JARVIS words in workspace
    replace_jarvis_with_arvis()

    # 1. Initialize SQLite Database
    print("📂 Initializing database...")
    ArvisMemory()
    
    # 2. Start background scheduler thread
    sched_thread = threading.Thread(target=scheduler_loop, daemon=True)
    sched_thread.start()
    
    # 4. Trigger auto-browser open (skip if running in Render cloud)
    if config.AUTO_OPEN_BROWSER and not IS_RENDER:
        def open_browser():
            time.sleep(2)
            webbrowser.open(f"http://127.0.0.1:{config.PORT}")
        threading.Thread(target=open_browser, daemon=True).start()
        
    # 5. Run Server
    # Render binds the port using the PORT env variable and requires hosting on 0.0.0.0
    host = "0.0.0.0" if IS_RENDER else "127.0.0.1"
    port = int(os.environ.get("PORT", config.PORT))
    print(f"🚀 Launching ARVIS AI Server on http://{host}:{port}...")
    socketio.run(app, host=host, port=port, debug=config.DEBUG)

if __name__ == "__main__":
    main()
