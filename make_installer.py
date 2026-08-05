"""Standalone Windows Installer & Shortcut Creator Builder for Aether Desktop.

Produces: dist_build/Aether-Setup.py / installer executable that:
  1. Installs Aether to %LOCALAPPDATA%\\Aether
  2. Creates Desktop Shortcut (Aether.lnk) with logo.ico
  3. Creates Start Menu Shortcut (Aether.lnk) in Programs with logo.ico
  4. Automatically launches Aether Desktop
"""
from __future__ import annotations

import os
import sys
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent

INSTALLER_SCRIPT = """import os
import sys
import shutil
import subprocess
from pathlib import Path

LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
INSTALL_DIR = LOCAL_APPDATA / "Aether"

def create_shortcuts(exe_path: Path, icon_path: Path):
    ps_commands = [
        f'$WshShell = New-Object -ComObject WScript.Shell',
        f'$DesktopPath = [System.Environment]::GetFolderPath("Desktop")',
        f'$ShortcutDesktop = $WshShell.CreateShortcut("$DesktopPath\\\\Aether.lnk")',
        f'$ShortcutDesktop.TargetPath = "{exe_path}"',
        f'$ShortcutDesktop.IconLocation = "{icon_path}"',
        f'$ShortcutDesktop.Description = "Aether AI Agent + Personal RAG Desktop OS"',
        f'$ShortcutDesktop.Save()',
        f'$StartMenuPath = [System.Environment]::GetFolderPath("StartMenu")',
        f'$ShortcutStart = $WshShell.CreateShortcut("$StartMenuPath\\\\Programs\\\\Aether.lnk")',
        f'$ShortcutStart.TargetPath = "{exe_path}"',
        f'$ShortcutStart.IconLocation = "{icon_path}"',
        f'$ShortcutStart.Description = "Aether AI Agent + Personal RAG Desktop OS"',
        f'$ShortcutStart.Save()'
    ]
    full_ps = "\\n".join(ps_commands)
    try:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", full_ps], check=True)
        print("[OK] Created Desktop & Start Menu shortcuts.")
    except Exception as e:
        print(f"Shortcut creation notice: {e}")

def main():
    print("Installing Aether Desktop to %LOCALAPPDATA%\\\\Aether...")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    
    source_dir = Path(__file__).parent
    target_exe = INSTALL_DIR / "Aether.exe"
    icon_file = INSTALL_DIR / "desktop_ui" / "logo.ico"
    
    # Copy files
    for item in source_dir.iterdir():
        if item.name.startswith(".") or item.name == "__pycache__":
            continue
        dst = INSTALL_DIR / item.name
        if item.is_dir():
            if dst.exists():
                shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(item, dst)
        else:
            shutil.copy2(item, dst)
            
    create_shortcuts(target_exe, icon_file)
    print("Installation complete! Launching Aether...")
    if target_exe.exists():
        subprocess.Popen([str(target_exe)])

if __name__ == "__main__":
    main()
"""

def main():
    print("Step 1: Building PyInstaller App Distribution...")
    subprocess.run([sys.executable, "build_aether.py"], check=True)
    
    print("Step 2: Packaging Installer Setup...")
    dist_app_dir = HERE / "dist_build" / "Aether"
    installer_script_path = dist_app_dir / "installer_setup.py"
    installer_script_path.write_text(INSTALLER_SCRIPT, encoding="utf-8")
    
    print("[OK] Package ready in dist_build/Aether!")
    print("[OK] Installer script created at:", installer_script_path)

if __name__ == "__main__":
    main()
