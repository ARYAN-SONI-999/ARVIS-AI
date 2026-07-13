"""
ARVIS System Control — Windows Power, Network, Audio & Display
Fixed:
  - Full PowerShell path used everywhere (no PATH dependency)
  - WiFi status works even when adapter is off/disconnected
  - Battery time overflow capped correctly
  - WiFi/BT UAC elevation uses full powershell.exe path
"""

import subprocess
import os
import sys
import time
import ctypes

# ── Full path to PowerShell — avoids PATH issues ──────────────
PS = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _run(cmd, capture=True, shell=True, timeout=15):
    """Run a shell command synchronously. Returns (success, output_str)."""
    try:
        result = subprocess.run(
            cmd, shell=shell, capture_output=capture,
            text=True, timeout=timeout
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        return result.returncode == 0, out or err
    except subprocess.TimeoutExpired:
        return False, "Command timed out."
    except Exception as e:
        return False, str(e)


def _ps(command: str, timeout: int = 15):
    """Run a PowerShell command using the full path. Returns (success, output)."""
    return _run(
        [PS, "-NoProfile", "-NonInteractive", "-Command", command],
        shell=False,
        timeout=timeout
    )


def _is_admin() -> bool:
    """Returns True if the current process has Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _elevate_and_run(ps_command: str) -> tuple[bool, str]:
    """Run a PowerShell command as Admin using UAC elevation.
    
    Returns (success: bool, msg: str)
    """
    try:
        proc = subprocess.Popen(
            [PS, "-NoProfile", "-Command",
             f"Start-Process '{PS}' -Verb RunAs "
             f"-ArgumentList '-NoProfile -Command \"{ps_command}\"'"],
            shell=False
        )
        time.sleep(1.5)
        return True, "UAC prompt triggered."
    except Exception as e:
        return False, str(e)


def _nircmd(args_str: str):
    """Run nircmd command if available."""
    return _run(f"nircmd {args_str}")


# ─────────────────────────────────────────────
# VOLUME CONTROL
# ─────────────────────────────────────────────

def set_volume(level: int) -> str:
    """Set system volume to a percentage (0-100)."""
    try:
        level = max(0, min(100, int(level)))
    except (ValueError, TypeError):
        return "❌ 'level' must be a number between 0 and 100."

    # Method 1: nircmd (best — silent, no admin, instant)
    ok, _ = _nircmd(f"setsysvolume {int(level * 655.35)}")
    if ok:
        return f"✅ Volume set to **{level}%**."

    # Method 2: PowerShell full path with WMI audio control
    ps_cmd = (
        f"$wshell = New-Object -ComObject wscript.shell; "
        f"1..50 | ForEach-Object {{ $wshell.SendKeys([char]174) }}; "
        f"1..{max(1, int(level / 2))} | ForEach-Object {{ $wshell.SendKeys([char]175) }}"
    )
    ok2, out2 = _ps(ps_cmd)
    if ok2:
        return f"✅ Volume set to approximately **{level}%**."

    # Method 3: PowerShell via keybd_event (most compatible)
    ok3, out3 = _ps(
        f"Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
        f"public class Audio {{ [DllImport(\"user32.dll\")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo); }}'; "
        f"for ($i = 0; $i -lt 50; $i++) {{ [Audio]::keybd_event(0xAE, 0, 0, 0) }}; "
        f"for ($i = 0; $i -lt {max(1, int(level / 2))}; $i++) {{ [Audio]::keybd_event(0xAF, 0, 0, 0) }}"
    )
    return f"✅ Volume adjusted to **{level}%**." if ok3 else f"❌ Volume control failed: {out3}"


def mute_volume() -> str:
    """Mute system audio."""
    # Method 1: nircmd
    ok, _ = _nircmd("mutesysvolume 1")
    if ok:
        return "✅ System audio **muted**."

    # Method 2: WASAPI via PowerShell Add-Type (Direct system-wide mute)
    ps = (
        "Add-Type -TypeDefinition '"
        "using System; using System.Runtime.InteropServices; "
        "[Guid(\"5CDF2C82-841E-4546-9722-0CF74078229A\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] "
        "interface IAudioEndpointVolume { "
        "  int f1(); int f2(); int f3(); int f4(); int f5(); int f6(); int f7(); int f8(); int f9(); int f10(); int f11(); "
        "  int SetMute([MarshalAs(UnmanagedType.Bool)] bool mute, ref Guid eventContext); "
        "  int GetMute(out bool mute); "
        "} "
        "[Guid(\"D666063F-1587-4E43-81F1-B948E807363F\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] "
        "interface IMMDevice { int Activate(ref Guid id, int clsCtx, IntPtr paramsPtr, out IAudioEndpointVolume volume); } "
        "[Guid(\"A95664D2-9614-4F35-A746-DE8DB63617E6\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] "
        "interface IMMDeviceEnumerator { int f1(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice device); } "
        "[ComImport, Guid(\"BCDE0395-E52F-467C-8E3D-C4579291692E\")] class MMDeviceEnumerator { } "
        "public class Vol { "
        "  public static void SetMute(bool m) { "
        "    var enumerator = (IMMDeviceEnumerator)(new MMDeviceEnumerator()); "
        "    IMMDevice device; enumerator.GetDefaultAudioEndpoint(0, 1, out device); "
        "    IAudioEndpointVolume volume; var iid = new Guid(\"5CDF2C82-841E-4546-9722-0CF74078229A\"); "
        "    device.Activate(ref iid, 23, IntPtr.Zero, out volume); "
        "    var dummy = Guid.Empty; volume.SetMute(m, ref dummy); "
        "  } "
        "}'; [Vol]::SetMute($true)"
    )
    ok2, out2 = _ps(ps)
    if ok2:
        return "✅ System audio **muted**."

    # Method 3: PowerShell key press toggle fallback
    ok3, out3 = _ps(
        "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
        "public class Audio { [DllImport(\"user32.dll\")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo); }'; "
        "[Audio]::keybd_event(0xAD, 0, 0, 0)"
    )
    return "✅ System audio **muted**." if ok3 else f"❌ Failed to mute: {out3}"


def unmute_volume() -> str:
    """Unmute system audio."""
    # Method 1: nircmd
    ok, _ = _nircmd("mutesysvolume 0")
    if ok:
        return "✅ System audio **unmuted**."

    # Method 2: WASAPI via PowerShell Add-Type (Direct system-wide unmute)
    ps = (
        "Add-Type -TypeDefinition '"
        "using System; using System.Runtime.InteropServices; "
        "[Guid(\"5CDF2C82-841E-4546-9722-0CF74078229A\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] "
        "interface IAudioEndpointVolume { "
        "  int f1(); int f2(); int f3(); int f4(); int f5(); int f6(); int f7(); int f8(); int f9(); int f10(); int f11(); "
        "  int SetMute([MarshalAs(UnmanagedType.Bool)] bool mute, ref Guid eventContext); "
        "  int GetMute(out bool mute); "
        "} "
        "[Guid(\"D666063F-1587-4E43-81F1-B948E807363F\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] "
        "interface IMMDevice { int Activate(ref Guid id, int clsCtx, IntPtr paramsPtr, out IAudioEndpointVolume volume); } "
        "[Guid(\"A95664D2-9614-4F35-A746-DE8DB63617E6\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] "
        "interface IMMDeviceEnumerator { int f1(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice device); } "
        "[ComImport, Guid(\"BCDE0395-E52F-467C-8E3D-C4579291692E\")] class MMDeviceEnumerator { } "
        "public class Vol { "
        "  public static void SetMute(bool m) { "
        "    var enumerator = (IMMDeviceEnumerator)(new MMDeviceEnumerator()); "
        "    IMMDevice device; enumerator.GetDefaultAudioEndpoint(0, 1, out device); "
        "    IAudioEndpointVolume volume; var iid = new Guid(\"5CDF2C82-841E-4546-9722-0CF74078229A\"); "
        "    device.Activate(ref iid, 23, IntPtr.Zero, out volume); "
        "    var dummy = Guid.Empty; volume.SetMute(m, ref dummy); "
        "  } "
        "}'; [Vol]::SetMute($false)"
    )
    ok2, out2 = _ps(ps)
    if ok2:
        return "✅ System audio **unmuted**."

    # Method 3: PowerShell toggle fallback
    ok3, out3 = _ps(
        "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
        "public class Audio { [DllImport(\"user32.dll\")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo); }'; "
        "[Audio]::keybd_event(0xAD, 0, 0, 0)"
    )
    return "✅ System audio **unmuted**." if ok3 else f"❌ Failed to unmute: {out3}"


# ─────────────────────────────────────────────
# BRIGHTNESS CONTROL (laptop displays only)
# ─────────────────────────────────────────────

def set_brightness(level: int) -> str:
    """Set display brightness to a percentage (0-100). Works on laptop displays only."""
    try:
        level = max(0, min(100, int(level)))
    except (ValueError, TypeError):
        return "❌ 'level' must be a number between 0 and 100."

    # Method 1: screen-brightness-control library
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        return f"✅ Brightness set to **{level}%**."
    except ImportError:
        pass
    except Exception:
        pass

    # Method 2: WMI via PowerShell full path
    ok, out = _ps(
        f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
        f".WmiSetBrightness(1,{level})"
    )
    if ok:
        return f"✅ Brightness set to **{level}%**."

    return (
        f"❌ Failed to set brightness: {out}\n"
        "Note: Brightness control works only on **laptop displays**."
    )


# ─────────────────────────────────────────────
# WIFI CONTROL  (auto-elevates via UAC)
# ─────────────────────────────────────────────

def _get_wifi_adapter() -> str | None:
    """Return the name of the first wireless network adapter (works even when off)."""
    # Method 1: PowerShell Get-NetAdapter (works even when adapter is disabled)
    ok, out = _ps(
        "Get-NetAdapter | Where-Object {"
        "  $_.PhysicalMediaType -like '*Wireless*' -or"
        "  $_.InterfaceDescription -like '*Wi-Fi*' -or"
        "  $_.InterfaceDescription -like '*Wireless*' -or"
        "  $_.Name -like '*Wi-Fi*'"
        "} | Select-Object -First 1 -ExpandProperty Name"
    )
    if ok and out:
        return out.strip()

    # Method 2: netsh interface show interface (shows all including disabled)
    ok2, out2 = _run("netsh interface show interface")
    if ok2:
        for line in out2.splitlines():
            if "Wi-Fi" in line or "Wireless" in line:
                # Line format: "Enabled  Connected  Wi-Fi"
                parts = line.strip().split()
                if parts:
                    return parts[-1]

    # Method 3: netsh wlan show interfaces (only works when WiFi is ON)
    ok3, out3 = _run("netsh wlan show interfaces")
    if ok3:
        for line in out3.splitlines():
            line = line.strip()
            if line.startswith("Name") and ":" in line:
                return line.split(":", 1)[1].strip()

    return None


def turn_on_wifi() -> str:
    """Enable the Wi-Fi adapter. Shows UAC prompt if not running as Administrator."""
    adapter = _get_wifi_adapter()

    if _is_admin():
        if not adapter:
            return "❌ Could not detect a Wi-Fi adapter on this system."
        ok, out = _run(f'netsh interface set interface "{adapter}" enabled')
        if ok:
            return f"✅ Wi-Fi turned **ON** (adapter: {adapter})."
        ok2, out2 = _ps(f"Enable-NetAdapter -Name '{adapter}' -Confirm:$false")
        return f"✅ Wi-Fi turned **ON**." if ok2 else f"❌ Failed to enable WiFi: {out2}"
    else:
        if adapter:
            ps_cmd = f"Enable-NetAdapter -Name '{adapter}' -Confirm:$false"
        else:
            ps_cmd = (
                "Get-NetAdapter | Where-Object {"
                "$_.PhysicalMediaType -like '*Wireless*' -or "
                "$_.InterfaceDescription -like '*Wi-Fi*'"
                "} | Select-Object -First 1 | Enable-NetAdapter -Confirm:$false"
            )
        ok, msg = _elevate_and_run(ps_cmd)
        name = adapter or "Wi-Fi adapter"
        if ok:
            return f"✅ UAC prompt shown — click **Yes** to turn on Wi-Fi ({name})."
        return f"❌ Failed to elevate for WiFi: {msg}"


def turn_off_wifi() -> str:
    """Disable the Wi-Fi adapter. Shows UAC prompt if not running as Administrator."""
    adapter = _get_wifi_adapter()

    if _is_admin():
        if not adapter:
            return "❌ Could not detect a Wi-Fi adapter on this system."
        ok, out = _run(f'netsh interface set interface "{adapter}" disabled')
        if ok:
            return f"✅ Wi-Fi turned **OFF** (adapter: {adapter})."
        ok2, out2 = _ps(f"Disable-NetAdapter -Name '{adapter}' -Confirm:$false")
        return f"✅ Wi-Fi turned **OFF**." if ok2 else f"❌ Failed to disable WiFi: {out2}"
    else:
        if adapter:
            ps_cmd = f"Disable-NetAdapter -Name '{adapter}' -Confirm:$false"
        else:
            ps_cmd = (
                "Get-NetAdapter | Where-Object {"
                "$_.PhysicalMediaType -like '*Wireless*' -or "
                "$_.InterfaceDescription -like '*Wi-Fi*'"
                "} | Select-Object -First 1 | Disable-NetAdapter -Confirm:$false"
            )
        ok, msg = _elevate_and_run(ps_cmd)
        name = adapter or "Wi-Fi adapter"
        if ok:
            return f"✅ UAC prompt shown — click **Yes** to turn off Wi-Fi ({name})."
        return f"❌ Failed to elevate for WiFi: {msg}"


def get_wifi_status() -> str:
    """Check WiFi connection status, SSID, and signal strength."""
    # Method 1: netsh wlan show interfaces (connected WiFi)
    ok, out = _run("netsh wlan show interfaces")
    if ok and out and "SSID" in out:
        info = {}
        for line in out.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                info[key.strip()] = val.strip()
        state  = info.get("State", "unknown")
        ssid   = info.get("SSID", "N/A")
        signal = info.get("Signal", "N/A")
        radio  = info.get("Radio type", "N/A")
        bssid  = info.get("BSSID", "N/A")
        return (
            f"📶 **Wi-Fi Status**\n"
            f"- State: **{state}**\n"
            f"- SSID: {ssid}\n"
            f"- Signal: {signal}\n"
            f"- BSSID: {bssid}\n"
            f"- Radio: {radio}"
        )

    # Method 2: Get-NetAdapter via PowerShell (works even when disconnected/off)
    ok2, out2 = _ps(
        "Get-NetAdapter | Where-Object {"
        "  $_.PhysicalMediaType -like '*Wireless*' -or"
        "  $_.InterfaceDescription -like '*Wi-Fi*'"
        "} | Select-Object Name, Status, LinkSpeed | Format-List"
    )
    if ok2 and out2:
        # Parse status from PowerShell output
        status_line = ""
        name_line = ""
        for line in out2.splitlines():
            if "Status" in line:
                status_line = line.split(":", 1)[-1].strip()
            if "Name" in line:
                name_line = line.split(":", 1)[-1].strip()

        emoji = "🟢" if status_line.lower() == "up" else "🔴"
        return (
            f"📶 **Wi-Fi Adapter Status**\n"
            f"- Adapter: {name_line}\n"
            f"- Status: {emoji} **{status_line}** (not connected to any network)\n"
            f"- Use `turn on wifi` to enable or check Windows Settings."
        )

    # Method 3: netsh interface show interface fallback
    ok3, out3 = _run("netsh interface show interface")
    if ok3:
        for line in out3.splitlines():
            if "Wi-Fi" in line or "Wireless" in line:
                parts = line.strip().split()
                state = parts[0] if parts else "Unknown"
                name  = parts[-1] if len(parts) > 1 else "Wi-Fi"
                return (
                    f"📶 **Wi-Fi Status**\n"
                    f"- Adapter: {name}\n"
                    f"- Admin State: **{state}**\n"
                    f"- Not connected to a network."
                )

    return "❌ No Wi-Fi adapter detected on this system."


# ─────────────────────────────────────────────
# BLUETOOTH CONTROL  (auto-elevates via UAC)
# ─────────────────────────────────────────────

_BT_FIND = (
    "$radios = [Windows.Devices.Radios.Radio,Windows.System.Devices,"
    "ContentType=WindowsRuntime]::GetRadiosAsync().GetAwaiter().GetResult(); "
    "$bt = $radios | Where-Object { $_.Kind -eq 'Bluetooth' }; "
)


def turn_on_bluetooth() -> str:
    """Enable Bluetooth. Shows UAC prompt if not running as Administrator."""
    ps = _BT_FIND + (
        "if ($bt) { $bt.SetStateAsync('On').GetAwaiter().GetResult() | Out-Null; 'OK' } "
        "else { 'NOT_FOUND' }"
    )
    if _is_admin():
        ok, out = _ps(ps)
        if "NOT_FOUND" in out:
            return "❌ No Bluetooth adapter found on this device."
        return "✅ Bluetooth turned **ON**." if ok else f"❌ Failed: {out}"
    else:
        ok, msg = _elevate_and_run(ps)
        if ok:
            return "✅ UAC prompt shown — click **Yes** to enable Bluetooth."
        return f"❌ Failed to elevate for Bluetooth: {msg}"


def turn_off_bluetooth() -> str:
    """Disable Bluetooth. Shows UAC prompt if not running as Administrator."""
    ps = _BT_FIND + (
        "if ($bt) { $bt.SetStateAsync('Off').GetAwaiter().GetResult() | Out-Null; 'OK' } "
        "else { 'NOT_FOUND' }"
    )
    if _is_admin():
        ok, out = _ps(ps)
        if "NOT_FOUND" in out:
            return "❌ No Bluetooth adapter found on this device."
        return "✅ Bluetooth turned **OFF**." if ok else f"❌ Failed: {out}"
    else:
        ok, msg = _elevate_and_run(ps)
        if ok:
            return "✅ UAC prompt shown — click **Yes** to disable Bluetooth."
        return f"❌ Failed to elevate for Bluetooth: {msg}"


# ─────────────────────────────────────────────
# POWER MANAGEMENT
# ─────────────────────────────────────────────

def lock_screen() -> str:
    """Lock the Windows session immediately."""
    try:
        # Direct Windows API call — most reliable
        ctypes.windll.user32.LockWorkStation()
        return "✅ Screen **locked**."
    except Exception:
        ok, out = _run("rundll32.exe user32.dll,LockWorkStation")
        return "✅ Screen locked." if ok else f"❌ Failed to lock screen: {out}"


def sleep_system() -> str:
    """Put the system to sleep."""
    ok, out = _run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    if ok:
        return "✅ System going to **sleep**..."
    ok2, out2 = _ps(
        "Add-Type -Assembly System.Windows.Forms; "
        "[System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false)"
    )
    return "✅ System going to sleep..." if ok2 else f"❌ Failed to sleep: {out}"


def shutdown_system(delay_seconds: int = 0) -> str:
    """Shutdown the PC. Use delay_seconds=0 for immediate shutdown."""
    try:
        delay = max(0, int(delay_seconds))
    except (ValueError, TypeError):
        delay = 0
    ok, out = _run(f"shutdown /s /t {delay}")
    if ok:
        msg = f"in **{delay} seconds**" if delay > 0 else "**now**"
        return f"✅ System will shutdown {msg}."
    return f"❌ Failed to initiate shutdown: {out}"


def restart_system(delay_seconds: int = 0) -> str:
    """Restart the PC. Use delay_seconds=0 for immediate restart."""
    try:
        delay = max(0, int(delay_seconds))
    except (ValueError, TypeError):
        delay = 0
    ok, out = _run(f"shutdown /r /t {delay}")
    if ok:
        msg = f"in **{delay} seconds**" if delay > 0 else "**now**"
        return f"✅ System will restart {msg}."
    return f"❌ Failed to initiate restart: {out}"


def cancel_shutdown() -> str:
    """Cancel a pending shutdown or restart."""
    ok, out = _run("shutdown /a")
    return "✅ Pending shutdown/restart **cancelled**." if ok else f"❌ No pending shutdown to cancel: {out}"


# ─────────────────────────────────────────────
# BATTERY INFO
# ─────────────────────────────────────────────

def get_battery_status() -> str:
    """Return current battery percentage and charging state."""
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery is None:
            return "❌ No battery found (this may be a desktop PC)."

        percent   = battery.percent
        plugged   = battery.power_plugged
        secs_left = battery.secsleft

        # Fix overflow: psutil returns huge numbers on some systems when charging
        # Cap at 30 hours (108000 seconds) as a sanity check
        MAX_SECS = 108_000  # 30 hours
        if plugged or secs_left <= 0 or secs_left > MAX_SECS:
            time_left = "Charging (plugged in)" if plugged else "Calculating..."
        else:
            h = int(secs_left) // 3600
            m = (int(secs_left) % 3600) // 60
            time_left = f"{h}h {m}m remaining"

        status = "🔌 Plugged In" if plugged else "🔋 On Battery"
        bar_filled = max(0, min(10, int(percent / 10)))
        bar = "█" * bar_filled + "░" * (10 - bar_filled)

        return (
            f"🔋 **Battery Status**\n"
            f"- Charge: **{percent:.0f}%** [{bar}]\n"
            f"- Status: {status}\n"
            f"- Time Left: {time_left}"
        )
    except ImportError:
        return "❌ psutil not installed. Run: `pip install psutil`"
    except Exception as e:
        return f"❌ Error reading battery info: {e}"
