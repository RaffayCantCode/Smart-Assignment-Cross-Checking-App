import os
import sys
import shutil
import subprocess
import ctypes


def show_error(message, title="Smart Assignment Checker"):
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        pass


def find_interpreter():
    for name in ("pythonw", "python", "py"):
        path = shutil.which(name)
        if path:
            return path
    return None


def main():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    main_py = os.path.join(base_dir, "main.py")
    if not os.path.isfile(main_py):
        show_error(
            "main.py was not found next to this program. The installation "
            "may be incomplete."
        )
        return

    interpreter = find_interpreter()
    if interpreter is None:
        show_error(
            "Python was not found on this computer.\n\n"
            "Install Python, then run 'Install Dependencies.bat' inside the "
            "application folder before launching."
        )
        return

    try:
        subprocess.Popen([interpreter, main_py], cwd=base_dir)
    except Exception as e:
        show_error(f"Could not start the application:\n{e}")


if __name__ == "__main__":
    main()
