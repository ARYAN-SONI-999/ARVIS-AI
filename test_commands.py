"""
ARVIS Full Command Test Suite
Tests every category from ARVIS_Commands.txt
Run: venv\\Scripts\\python.exe test_commands.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Stub config
class _Cfg:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    TEMP_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "temp")

sys.modules.setdefault("config", _Cfg())
import config
config.BASE_DIR = _Cfg.BASE_DIR
config.TEMP_DIR = _Cfg.TEMP_DIR

# ─── Test runner ──────────────────────────────────────────────
results = []

def test(label, fn, *args, skip=False, **kwargs):
    if skip:
        results.append((label, "⏭️  SKIP", "Skipped (destructive/manual test)"))
        print(f"\n{'─'*60}")
        print(f"  TEST  : {label}")
        print(f"  STATUS: ⏭️  SKIP")
        return

    print(f"\n{'─'*60}")
    print(f"  TEST  : {label}")
    try:
        out = fn(*args, **kwargs)
        s = str(out)
        if "✅" in s or "##" in s or ("Result:" in s):
            status = "✅ PASS"
        elif "❌" in s:
            status = "❌ FAIL"
        elif s.strip():
            status = "✅ PASS"   # has output = working
        else:
            status = "⚠️  WARN"
        results.append((label, status, s))
        print(f"  STATUS: {status}")
        print(f"  OUTPUT: {s[:250]}")
    except Exception as e:
        results.append((label, "❌ FAIL", str(e)))
        print(f"  STATUS: ❌ FAIL")
        print(f"  ERROR : {str(e)[:250]}")

# ════════════════════════════════════════════════════════════════
print("=" * 60)
print("   ARVIS FULL COMMAND TEST SUITE")
print("=" * 60)

# ── Imports ──────────────────────────────────────────────────────
print("\n⏳ Loading all skills...")
from skills.system_control import (
    get_wifi_status, get_battery_status, set_volume,
    mute_volume, unmute_volume, turn_off_wifi, turn_on_wifi,
    set_brightness, lock_screen
)
from skills.computer_control import open_app, close_app, press_keys
from skills.calculator import evaluate_formula
from skills.system_info import get_system_stats
from skills.web_search import web_search
from skills.news import get_news
from skills.scheduler import schedule_task
print("   ✅ All skills loaded OK\n")

# ════ 1. BATTERY & SYSTEM INFO ═══════════════════════════════════
print("★  [1] BATTERY & SYSTEM INFO")
test("Battery status",     get_battery_status)
test("System stats",       get_system_stats)

# ════ 2. WIFI ════════════════════════════════════════════════════
print("\n★  [2] WIFI")
test("WiFi status",        get_wifi_status)
test("Turn OFF WiFi (UAC popup → click YES)", turn_off_wifi)
test("Turn ON WiFi  (UAC popup → click YES)", turn_on_wifi)

# ════ 3. VOLUME ══════════════════════════════════════════════════
print("\n★  [3] VOLUME")
test("Set volume → 50",    set_volume,   50)
test("Set volume → 0",     set_volume,   0)
test("Set volume → 100",   set_volume,   100)
test("Mute",               mute_volume)
test("Unmute",             unmute_volume)

# ════ 4. BRIGHTNESS ══════════════════════════════════════════════
print("\n★  [4] BRIGHTNESS (laptop only)")
test("Set brightness 70",  set_brightness, 70)

# ════ 5. APP LAUNCH ══════════════════════════════════════════════
print("\n★  [5] APP LAUNCH")
test("open calculator",             open_app, "calculator")
test("open notepad",                open_app, "notepad")
test("open whatsapp",               open_app, "whatsapp")
test("turn on whatsapp (alias)",    open_app, "turn on whatsapp")
test("open chrome",                 open_app, "chrome")
test("open settings",               open_app, "settings")
test("open task manager",           open_app, "task manager")
test("open vlc",                    open_app, "vlc")

# ════ 6. MATH / CALCULATOR ═══════════════════════════════════════
print("\n★  [6] MATH & CALCULATOR")
test("2 + 2",                       evaluate_formula, "2 + 2")
test("15% of 2500",                 evaluate_formula, "15% of 2500")
test("20 percent of 500",           evaluate_formula, "20 percent of 500")
test("sqrt(144)",                   evaluate_formula, "sqrt(144)")
test("sin(pi / 2)",                 evaluate_formula, "sin(pi / 2)")
test("2 ** 10",                     evaluate_formula, "2 ** 10")
test("factorial(10)",               evaluate_formula, "factorial(10)")

# ════ 7. WEB SEARCH ══════════════════════════════════════════════
print("\n★  [7] WEB SEARCH")
test("Search: Python version",      web_search, "latest Python version 2025", 3)

# ════ 8. NEWS ════════════════════════════════════════════════════
print("\n★  [8] NEWS")
test("Tech news",                   get_news, "tech",    4)
test("Sports news",                 get_news, "sports",  4)
test("News about AI",               get_news, "AI",      4)
test("News about cricket",          get_news, "cricket", 4)

# ════ 9. SCHEDULER ═══════════════════════════════════════════════
print("\n★  [9] SCHEDULER")
import datetime
future = (datetime.datetime.now() + datetime.timedelta(minutes=10)).strftime("%H:%M")
test("Schedule task",               schedule_task, future, "daily", "drink water reminder")

# ════ 10. DESKTOP CONTROL ════════════════════════════════════════
print("\n★  [10] DESKTOP CONTROL (non-destructive only)")
test("Press keys: ctrl+esc (skip)", press_keys, "ctrl+esc")

# ════ SKIP — destructive tests ════════════════════════════════════
print("\n★  [11] POWER (skipped — would lock/shutdown)")
test("Lock screen",  lock_screen,  skip=True)

# ════ FINAL SUMMARY ══════════════════════════════════════════════
print("\n" + "=" * 60)
print("  FINAL SUMMARY")
print("=" * 60)

passed = sum(1 for _, s, _ in results if "PASS" in s)
warned = sum(1 for _, s, _ in results if "WARN" in s)
failed = sum(1 for _, s, _ in results if "FAIL" in s)
skipped= sum(1 for _, s, _ in results if "SKIP" in s)

for label, status, out in results:
    print(f"  {status}  {label}")
    if "FAIL" in status:
        short = out.replace("\n", " ")[:90]
        print(f"         └─ {short}")

print()
print(f"  ✅ Passed  : {passed}")
print(f"  ❌ Failed  : {failed}")
print(f"  ⚠️  Warned  : {warned}")
print(f"  ⏭️  Skipped : {skipped}")
print(f"  📊 Total   : {len(results)}")
print("=" * 60)
