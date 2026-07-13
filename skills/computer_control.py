"""
ARVIS Computer Control — App Launcher with 6-layer fallback
Fixed: WhatsApp, Telegram, Discord UWP launch + alias normalization
"""
import os
import glob
import subprocess
import time
import pyautogui
import pygetwindow as gw
import config

# Configure PyAutoGUI fail-safe
pyautogui.FAILSAFE = True

# Global list to hold process references to prevent Python 3.14 ResourceWarnings
SPAWNED_PROCESSES = []

# ── Alias normalization — maps natural language to canonical app name ──────────
ALIASES = {
    # WhatsApp variants
    "whatsapp":         "whatsapp",
    "what's app":       "whatsapp",
    "whats app":        "whatsapp",
    # Telegram variants
    "telegram":         "telegram",
    "tg":               "telegram",
    # Calculator
    "calc":             "calculator",
    "calculator":       "calculator",
    # VS Code
    "vscode":           "vscode",
    "vs code":          "vscode",
    "visual studio code": "vscode",
    "code":             "vscode",
    # Browsers
    "chrome":           "chrome",
    "google chrome":    "chrome",
    "edge":             "edge",
    "microsoft edge":   "edge",
    "firefox":          "firefox",
    "mozilla firefox":  "firefox",
    # Music
    "spotify":          "spotify",
    # Productivity
    "word":             "word",
    "microsoft word":   "word",
    "excel":            "excel",
    "microsoft excel":  "excel",
    "powerpoint":       "powerpoint",
    "microsoft powerpoint": "powerpoint",
    "ppt":              "powerpoint",
    # Communication
    "discord":          "discord",
    "zoom":             "zoom",
    "teams":            "teams",
    "microsoft teams":  "teams",
    # System
    "notepad":          "notepad",
    "paint":            "paint",
    "cmd":              "cmd",
    "command prompt":   "cmd",
    "powershell":       "powershell",
    "explorer":         "explorer",
    "file explorer":    "explorer",
    "taskmgr":          "taskmgr",
    "task manager":     "taskmgr",
    "settings":         "settings",
    "windows settings": "settings",
    # Media
    "vlc":              "vlc",
    "vlc media player": "vlc",
    # Other
    "steam":            "steam",
    "snipping":         "snipping",
    "snipping tool":    "snipping",
    "snip":             "snipping",
    "7zip":             "7zip",
    "7-zip":            "7zip",
    "wordpad":          "wordpad",
}


def clean_completed_processes():
    global SPAWNED_PROCESSES
    SPAWNED_PROCESSES = [p for p in SPAWNED_PROCESSES if p.poll() is None]


def _get_env():
    local = os.environ.get("LOCALAPPDATA", "")
    roaming = os.environ.get("APPDATA", "")
    return local, roaming


def _find_first_existing(*paths):
    """Return the first path that exists (supports glob patterns)."""
    for p in paths:
        if "*" in p or "?" in p:
            matches = glob.glob(p)
            if matches:
                return matches[0]
        elif os.path.exists(p):
            return p
    return None


def _launch(path_or_cmd: str, shell: bool = True, wait: float = 1.5) -> bool:
    """Launch a command/path and append to tracked process list. Returns True if Popen succeeded."""
    try:
        clean_completed_processes()
        proc = subprocess.Popen(path_or_cmd, shell=shell)
        SPAWNED_PROCESSES.append(proc)
        time.sleep(wait)
        return True
    except Exception:
        return False


def _resolve_exe(app: str) -> str | None:
    """Return the absolute .exe path for known apps, or None if not found."""
    local, roaming = _get_env()

    paths_map = {
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(local, r"Google\Chrome\Application\chrome.exe"),
        ],
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "firefox": [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        ],
        "vscode": [
            os.path.join(local, r"Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ],
        "spotify": [
            os.path.join(roaming, r"Spotify\Spotify.exe"),
            os.path.join(local, r"Microsoft\WindowsApps\Spotify.exe"),
        ],
        "calculator": [
            r"C:\Windows\System32\calc.exe",
            os.path.join(local, r"Microsoft\WindowsApps\Microsoft.WindowsCalculator_8wekyb3d8bbwe\Calculator.exe"),
        ],
        "notepad": [
            r"C:\Windows\System32\notepad.exe",
            r"C:\Windows\notepad.exe",
        ],
        "paint": [r"C:\Windows\System32\mspaint.exe"],
        "cmd":   [r"C:\Windows\System32\cmd.exe"],
        "powershell": [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"],
        "explorer":   [r"C:\Windows\explorer.exe"],
        "taskmgr":    [r"C:\Windows\System32\taskmgr.exe"],
        "wordpad": [r"C:\Program Files\Windows NT\Accessories\wordpad.exe"],
        "snipping": [
            r"C:\Windows\System32\SnippingTool.exe",
            os.path.join(local, r"Microsoft\WindowsApps\SnippingTool.exe"),
        ],
        "vlc": [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ],
        "zoom": [
            os.path.join(roaming, r"Zoom\bin\Zoom.exe"),
            os.path.join(local, r"Zoom\bin\Zoom.exe"),
        ],
        "teams": [
            os.path.join(local, r"Microsoft\Teams\current\Teams.exe"),
            os.path.join(local, r"Microsoft\Teams\Update.exe"),
        ],
        "word": [
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
        ],
        "excel": [
            r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
        ],
        "powerpoint": [
            r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE",
        ],
        # WhatsApp — installed from web (not Store)
        "whatsapp": [
            os.path.join(local, r"WhatsApp\WhatsApp.exe"),
            os.path.join(local, r"Programs\WhatsApp\WhatsApp.exe"),
            # Sometimes under WindowsApps with version glob
            os.path.join(local, r"Microsoft\WindowsApps\WhatsApp.exe"),
        ],
        # Telegram — installed from website
        "telegram": [
            os.path.join(roaming, r"Telegram Desktop\Telegram.exe"),
            os.path.join(local, r"Telegram Desktop\Telegram.exe"),
            os.path.join(local, r"Programs\Telegram Desktop\Telegram.exe"),
        ],
        # Discord — has version-numbered subfolder
        "discord": [
            # Glob for versioned app folder
            os.path.join(local, r"Discord\app-*\Discord.exe"),
            os.path.join(local, r"Discord\Discord.exe"),
        ],
        "steam": [
            r"C:\Program Files (x86)\Steam\steam.exe",
            r"C:\Program Files\Steam\steam.exe",
        ],
        "7zip": [
            r"C:\Program Files\7-Zip\7zFM.exe",
            r"C:\Program Files (x86)\7-Zip\7zFM.exe",
        ],
    }

    paths = paths_map.get(app, [])
    return _find_first_existing(*paths) if paths else None


# UWP protocol URIs — work without admin, no package ID needed
UWP_PROTOCOLS = {
    "whatsapp":   "whatsapp:",          # official WhatsApp protocol
    "ms-chat":    "ms-chat:",
    "settings":   "ms-settings:",
    "wifi":       "ms-settings:network-wifi",
    "bluetooth":  "ms-settings:bluetooth",
}

# UWP AppsFolder shell URIs — fallback if protocol doesn't work
UWP_SHELL = {
    "calculator": "shell:AppsFolder\\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App",
    "spotify":    "shell:AppsFolder\\SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify",
    "whatsapp":   "shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!WhatsAppDesktop",
    "telegram":   "shell:AppsFolder\\TelegramMessengerLLP.TelegramDesktop_t4vj0kkmxnwa4!Telegram",
    "xbox":       "shell:AppsFolder\\Microsoft.XboxApp_8wekyb3d8bbwe!Microsoft.XboxApp",
}


def open_app(app_name: str) -> str:
    """
    Opens a desktop or UWP application by name.
    Supports natural language aliases like 'open whatsapp', 'launch chrome', etc.
    Launch priority: direct .exe → protocol URI → UWP shell → PATH → Windows Search
    """
    # Normalize: strip action words and look up alias
    raw = app_name.lower().strip()
    for prefix in ("open ", "launch ", "start ", "run ", "turn on ", "show "):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
    app = ALIASES.get(raw, raw)

    # ── Layer 1: Direct .exe path ──────────────────────────────────────────────
    exe = _resolve_exe(app)
    if exe:
        if _launch(f'"{exe}"'):
            return f"✅ Successfully launched '{app_name}'."

    # ── Layer 2: Protocol URI (whatsapp:, ms-settings:, etc.) ─────────────────
    protocol = UWP_PROTOCOLS.get(app)
    if protocol:
        if _launch(f'start "" "{protocol}"', wait=2.0):
            return f"✅ Successfully launched '{app_name}' via protocol."

    # ── Layer 3: UWP shell:AppsFolder URI ─────────────────────────────────────
    shell_uri = UWP_SHELL.get(app)
    if shell_uri:
        if _launch(f'explorer "{shell_uri}"', wait=2.0):
            return f"✅ Successfully launched '{app_name}' (Store app)."

    # ── Layer 4: Simple PATH command ──────────────────────────────────────────
    simple_commands = {
        "chrome": "start chrome", "edge": "start msedge",
        "firefox": "start firefox", "notepad": "notepad.exe",
        "calculator": "calc.exe", "vscode": "code",
        "cmd": "start cmd.exe", "powershell": "start powershell.exe",
        "paint": "mspaint.exe", "explorer": "explorer.exe",
        "taskmgr": "taskmgr.exe", "vlc": "vlc.exe",
        "zoom": "zoom.exe", "teams": "teams.exe",
        "word": "winword.exe", "excel": "excel.exe",
        "powerpoint": "powerpnt.exe", "discord": "discord.exe",
        "steam": "steam.exe", "whatsapp": "WhatsApp.exe",
        "telegram": "telegram.exe", "spotify": "spotify.exe",
        "snipping": "snippingtool.exe", "wordpad": "wordpad.exe",
        "settings": "start ms-settings:",
    }
    cmd = simple_commands.get(app, app_name)
    if _launch(cmd):
        return f"✅ Successfully launched '{app_name}'."

    # ── Layer 5: Windows Search GUI fallback ──────────────────────────────────
    try:
        pyautogui.press("win")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(1.5)
        return f"✅ GUI launch fallback for '{app_name}' via Windows Start Menu."
    except Exception as e:
        return f"❌ Could not open '{app_name}'. Error: {e}"


def close_app(window_title: str) -> str:
    """Attempts to find and close a window with matching title."""
    try:
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            all_windows = gw.getAllWindows()
            windows = [w for w in all_windows if window_title.lower() in w.title.lower()]
        if not windows:
            return f"No open window found matching '{window_title}'."
        closed = []
        for w in windows:
            if w.title.strip():
                w.close()
                closed.append(w.title)
        return f"✅ Closed windows: {', '.join(closed)}"
    except Exception as e:
        return f"❌ Error closing window '{window_title}': {e}"


def take_screenshot() -> str:
    """Captures a full screenshot and saves it to the static assets directory."""
    try:
        save_dir = os.path.join(config.BASE_DIR, "static", "assets")
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, "screenshot.png")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        screenshot = pyautogui.screenshot()
        screenshot.save(file_path)
        return f"✅ Screenshot captured successfully and saved to: {file_path}"
    except Exception as e:
        return f"❌ Failed to capture screenshot: {e}"


def type_text(text: str) -> str:
    """Types out text at current cursor location."""
    try:
        pyautogui.write(text, interval=0.01)
        return f"✅ Typed: '{text}'"
    except Exception as e:
        return f"❌ Failed to type text: {e}"


def click_at(x, y) -> str:
    """Moves mouse and clicks at coordinate x, y."""
    try:
        pyautogui.click(int(x), int(y))
        return f"✅ Clicked at ({x}, {y})."
    except Exception as e:
        return f"❌ Failed to click at ({x}, {y}): {e}"


def press_keys(keys: str) -> str:
    """Presses key combination separated by + (e.g. ctrl+c, ctrl+alt+del)."""
    try:
        key_list = [k.strip().lower() for k in keys.split("+")]
        pyautogui.hotkey(*key_list)
        return f"✅ Pressed: `{keys}`"
    except Exception as e:
        return f"❌ Failed to press '{keys}': {e}"


def focus_window(window_title: str) -> str:
    """Brings a window matching the title to the foreground."""
    try:
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            all_windows = gw.getAllWindows()
            windows = [w for w in all_windows if window_title.lower() in w.title.lower()]
        if not windows:
            return f"No open window found matching '{window_title}'."
        w = windows[0]
        if w.isMinimized:
            w.restore()
        w.activate()
        return f"✅ Successfully focused window: '{w.title}'."
    except Exception as e:
        return f"❌ Error focusing window '{window_title}': {e}"
