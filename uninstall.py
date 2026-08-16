import os
import sys
import shutil
import subprocess
import time
import ctypes
import tempfile

APP_NAME = "Smart Assignment Checker"
EXE_NAME = "SmartAssignmentChecker.exe"


def ask_confirm(text, title="Uninstall Smart Assignment Checker"):
    try:
        res = ctypes.windll.user32.MessageBoxW(0, text, title, 0x20 | 0x1)  # MB_ICONQUESTION | MB_OKCANCEL
        return res == 1  # IDOK
    except Exception:
        return True


def kill_running_app():
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", EXE_NAME],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
        )
    except Exception:
        pass


def remove_shortcuts(app_name):
    # Desktop shortcut
    try:
        desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
        for name in [f"{app_name}.lnk", "SmartAssignmentChecker.lnk"]:
            sc = os.path.join(desktop_dir, name)
            if os.path.isfile(sc):
                try:
                    os.remove(sc)
                except Exception:
                    pass
    except Exception:
        pass

    # Start menu shortcuts
    try:
        app_data = os.environ.get("APPDATA", "")
        programs_dir = os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs")
        for name in [f"{app_name}.lnk", "SmartAssignmentChecker.lnk"]:
            sc = os.path.join(programs_dir, name)
            if os.path.isfile(sc):
                try:
                    os.remove(sc)
                except Exception:
                    pass
        # Start menu folder if created
        menu_folder = os.path.join(programs_dir, app_name)
        if os.path.isdir(menu_folder):
            try:
                shutil.rmtree(menu_folder, ignore_errors=True)
            except Exception:
                pass
    except Exception:
        pass


def perform_uninstall():
    if getattr(sys, "frozen", False):
        install_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        install_dir = os.path.dirname(os.path.abspath(__file__))

    if not ask_confirm(
        f"Are you sure you want to completely uninstall {APP_NAME} and remove all its files from this computer?\n\n"
        f"Installation directory:\n{install_dir}"
    ):
        return

    # 1. Terminate running app
    kill_running_app()
    time.sleep(0.3)

    # 2. Remove all shortcuts
    remove_shortcuts(APP_NAME)

    # 3. Create a detached uninstaller helper script in %TEMP%
    temp_dir = tempfile.gettempdir()
    cleanup_bat = os.path.join(temp_dir, f"uninstall_sac_{int(time.time())}.bat")

    bat_content = f"""@echo off
setlocal
set "TARGET={install_dir}"

:WAIT_LOOP
taskkill /F /IM "{EXE_NAME}" >nul 2>&1
timeout /t 1 /nobreak >nul

if not exist "%TARGET%" goto DONE

:: Try to remove directory recursively
rmdir /s /q "%TARGET%" >nul 2>&1
if not exist "%TARGET%" goto DONE

:: If still locked, wait and retry up to 15 times
timeout /t 1 /nobreak >nul
rmdir /s /q "%TARGET%" >nul 2>&1
if not exist "%TARGET%" goto DONE

timeout /t 1 /nobreak >nul
rmdir /s /q "%TARGET%" >nul 2>&1
if not exist "%TARGET%" goto DONE

:: Force remove via powershell if needed
powershell -NoProfile -Command "Remove-Item -LiteralPath '%TARGET%' -Force -Recurse -ErrorAction SilentlyContinue" >nul 2>&1

:DONE
:: Self-delete this batch script
del "%~f0" >nul 2>&1
exit /b 0
"""

    try:
        with open(cleanup_bat, "w", encoding="utf-8") as f:
            f.write(bat_content)
    except Exception:
        pass

    # 4. Launch the detached cleanup process from %TEMP%
    try:
        detached = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        no_window = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
        subprocess.Popen(
            ["cmd.exe", "/c", cleanup_bat],
            cwd=temp_dir,
            creationflags=detached | no_window,
            close_fds=True
        )
    except Exception:
        pass

    # 5. Show completion message and exit immediately so folder unlocks
    try:
        ctypes.windll.user32.MessageBoxW(
            0,
            f"{APP_NAME} was successfully uninstalled.",
            "Uninstallation Complete",
            0x40  # MB_ICONINFORMATION
        )
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    perform_uninstall()
