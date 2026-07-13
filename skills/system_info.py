import psutil
import platform
import os
import getpass
import datetime

def get_system_stats():
    """Gathers CPU, memory, disk, battery, and platform info.
    
    Returns a formatted string of system parameters.
    """
    try:
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        disk = psutil.disk_usage('C:\\')
        disk_usage = disk.percent
        
        # Get battery details if notebook
        battery_str = "N/A"
        if hasattr(psutil, "sensors_battery"):
            battery = psutil.sensors_battery()
            if battery:
                plugged = "Plugged In" if battery.power_plugged else "Not Plugged In"
                battery_str = f"{battery.percent}% ({plugged})"
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user = getpass.getuser()
        os_name = f"{platform.system()} {platform.release()}"
        
        stats = (
            f"--- System Stats ({now}) ---\n"
            f"OS: {os_name}\n"
            f"Active User: {user}\n"
            f"CPU Usage: {cpu_usage}%\n"
            f"RAM Usage: {memory_usage}% (Used: {memory.used // (1024**2)}MB, Total: {memory.total // (1024**2)}MB)\n"
            f"Disk Usage: {disk_usage}% (Free: {disk.free // (1024**3)}GB, Total: {disk.total // (1024**3)}GB)\n"
            f"Battery Status: {battery_str}\n"
        )
        return stats
    except Exception as e:
        return f"Error gathering system stats: {str(e)}"
