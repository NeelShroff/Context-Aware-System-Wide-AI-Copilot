import os
import sys
import argparse
import winreg
from pathlib import Path

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "System-Wide AI Copilot"


def get_vbs_launcher_path() -> Path:
    project_root = Path(__file__).resolve().parent.parent
    return project_root / "Launch Copilot.vbs"


def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"Error checking registry: {e}")
        return False


def set_autostart(enable: bool) -> bool:
    vbs_path = get_vbs_launcher_path()
    if not vbs_path.exists():
        print(f"Launcher path not found: {vbs_path}")
        return False

    cmd = f'wscript.exe "{vbs_path}"'

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                print("Auto-start enabled successfully.")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    print("Auto-start disabled successfully.")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"Failed to set autostart in Registry: {e}")
        return False


def create_shortcuts() -> bool:
    vbs_path = get_vbs_launcher_path()
    project_root = vbs_path.parent

    # Find pythonw or icon if available
    desktop = Path(os.path.expanduser("~/Desktop"))
    start_menu = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs"

    shortcut_vbs = project_root / "scripts" / "_create_lnk.vbs"
    shortcut_vbs.parent.mkdir(parents=True, exist_ok=True)

    custom_ico = Path(os.path.expanduser("~")) / "AppData" / "Local" / "System-Wide AI Copilot" / "app_icon.ico"
    if not custom_ico.exists():
        custom_ico = project_root / "assets" / "app_icon.ico"
    icon_str = str(custom_ico)

    vbs_script_content = f"""Set WshShell = CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")
strStartMenu = WshShell.SpecialFolders("Programs")

desktopFolders = Array(strDesktop, WshShell.ExpandEnvironmentStrings("%USERPROFILE%\\OneDrive\\Desktop"), WshShell.ExpandEnvironmentStrings("%PUBLIC%\\Desktop"))

For Each folder In desktopFolders
    If CreateObject("Scripting.FileSystemObject").FolderExists(folder) Then
        Set shortcut = WshShell.CreateShortcut(folder & "\\System-Wide AI Copilot.lnk")
        shortcut.TargetPath = "wscript.exe"
        shortcut.Arguments = Chr(34) & "{vbs_path}" & Chr(34)
        shortcut.WorkingDirectory = "{project_root}"
        shortcut.IconLocation = "{icon_str},0"
        shortcut.Description = "System-Wide AI Copilot Desktop App"
        shortcut.Save
    End If
Next

Set shortcut2 = WshShell.CreateShortcut(strStartMenu & "\\System-Wide AI Copilot.lnk")
shortcut2.TargetPath = "wscript.exe"
shortcut2.Arguments = Chr(34) & "{vbs_path}" & Chr(34)
shortcut2.WorkingDirectory = "{project_root}"
shortcut2.IconLocation = "{icon_str},0"
shortcut2.Description = "System-Wide AI Copilot Desktop App"
shortcut2.Save
"""
    with open(shortcut_vbs, "w", encoding="utf-8") as f:
        f.write(vbs_script_content)

    os.system(f'cscript //Nologo "{shortcut_vbs}"')
    if shortcut_vbs.exists():
        os.remove(shortcut_vbs)
    print("Desktop & Start Menu shortcuts created successfully.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Manage System-Wide AI Copilot Startup & Shortcuts")
    parser.add_argument("--status", action="store_true", help="Check auto-start status")
    parser.add_argument("--enable", action="store_true", help="Enable auto-start on boot")
    parser.add_argument("--disable", action="store_true", help="Disable auto-start on boot")
    parser.add_argument("--toggle", action="store_true", help="Toggle auto-start state")
    parser.add_argument("--create-shortcuts", action="store_true", help="Create Desktop & Start Menu shortcuts")

    args = parser.parse_args()

    if args.status:
        enabled = is_autostart_enabled()
        print("ENABLED" if enabled else "DISABLED")
    elif args.enable:
        set_autostart(True)
    elif args.disable:
        set_autostart(False)
    elif args.toggle:
        current = is_autostart_enabled()
        set_autostart(not current)
    elif args.create_shortcuts:
        create_shortcuts()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
