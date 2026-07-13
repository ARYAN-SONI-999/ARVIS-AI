import os
import json
import uuid
import datetime
import config

TASK_FILE = os.path.join(config.TEMP_DIR, "scheduler_tasks.json")

def load_scheduler_tasks():
    if not os.path.exists(TASK_FILE):
        return []
    try:
        with open(TASK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_scheduler_tasks(tasks):
    try:
        os.makedirs(os.path.dirname(TASK_FILE), exist_ok=True)
        with open(TASK_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
        return True
    except Exception:
        return False

def schedule_task(time_str, schedule_type, prompt):
    """Saves a background scheduled prompt.
    
    time_str: HH:MM, :MM, MM or YYYY-MM-DD HH:MM.
    schedule_type: once, daily, hourly.
    """
    type_clean = schedule_type.lower().strip()
    if type_clean not in ["once", "daily", "hourly"]:
        return "Error: Schedule type must be 'once', 'daily', or 'hourly'."
        
    # Basic format validation
    if type_clean == "once":
        try:
            datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return "Error: For 'once' schedules, time must match YYYY-MM-DD HH:MM format."
    elif type_clean == "hourly":
        # Accept either ":30" or "30" or "00:30" for hourly
        if ":" not in time_str:
            time_str = f"00:{time_str.zfill(2)}"
        elif time_str.startswith(":"):
            time_str = f"00{time_str}"
        try:
            datetime.datetime.strptime(time_str, "%H:%M")
        except ValueError:
            return "Error: For hourly, use MM or :MM format (e.g., '30' or ':30' = at :30 each hour)."
    else:
        try:
            datetime.datetime.strptime(time_str, "%H:%M")
        except ValueError:
            return "Error: For daily schedules, time must match HH:MM (24h) format."

    tasks = load_scheduler_tasks()
    
    task_id = str(uuid.uuid4())[:8]
    new_task = {
        "id": task_id,
        "time": time_str,
        "schedule": type_clean,
        "prompt": prompt,
        "status": "idle",
        "last_run": None,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    tasks.append(new_task)
    if save_scheduler_tasks(tasks):
        return f"Task scheduled successfully. ID: {task_id}, Type: {type_clean}, Time: {time_str}."
    else:
        return "Error: Failed to save the scheduled task to database."
