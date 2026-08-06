import os
import sys
import zipfile
import shutil
import subprocess

"""
build_setup.py

Developer build script. Run this to produce a shareable setup.exe FAST:

    python build_setup.py

What it does:

  1. LAUNCHER - compiles the tiny launcher.py into SmartAssignmentChecker.exe
                (a real .exe that starts the app with the installed Python).
  2. PACKAGE  - compresses the runnable project source (backend, gui, styles,
                main.py, requirements.txt) together with that launcher exe
                into dist/SmartAssignmentChecker-Source.zip.
  3. SETUP    - compiles Setup.py (the installer) into a single, portable
                dist/setup.exe with that package embedded inside it.

Distribute dist/setup.exe on your site. When a user runs it, the wizard
extracts the whole project into a folder of their choice - that folder
contains SmartAssignmentChecker.exe which they double-click to start the app.

Note: the target machine still needs Python with the app dependencies installed
(requirements.txt). The extracted folder includes "Install Dependencies.bat"
to make that one click. This keeps the build (and the installer) small.
"""

SETUP_EXE = "setup.exe"
INSTALLER_SCRIPT = "Setup.py"
SOURCE_ZIP = "SmartAssignmentChecker-Source.zip"
LAUNCHER_SRC = "launcher.py"
LAUNCHER_EXE = "SmartAssignmentChecker.exe"

APP_NAME = "Smart Assignment Checker"
DEPS_SCRIPT = "Install Dependencies.bat"

DEPS_SCRIPT_CONTENT = (
    '@echo off\r\n'
    'cd /d "%~dp0"\r\n'
    'echo Installing app dependencies...\r\n'
    'where py >nul 2>nul\r\n'
    'if %errorlevel%==0 (\r\n'
    '    py -m pip install -r requirements.txt\r\n'
    ') else (\r\n'
    '    python -m pip install -r requirements.txt\r\n'
    ')\r\n'
    'echo.\r\n'
    'echo Done. You can now run SmartAssignmentChecker.exe to start the app.\r\n'
    'pause\r\n'
)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
SOURCE_ZIP_PATH = os.path.join(DIST_DIR, SOURCE_ZIP)
SETUP_OUTPUT_PATH = os.path.join(DIST_DIR, SETUP_EXE)
LAUNCHER_OUTPUT_PATH = os.path.join(DIST_DIR, LAUNCHER_EXE)

SOURCE_TOP_FILES = ["main.py", "requirements.txt"]
SOURCE_PACKAGES = ["backend", "gui", "styles"]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def ensure_pyinstaller() -> bool:
    try:
        import PyInstaller  # noqa: F401
        print("PyInstaller is available.")
        return True
    except ImportError:
        print("PyInstaller not found - installing it now...")
        return subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"]).returncode == 0


def run(cmd, cwd=PROJECT_ROOT) -> int:
    print("+ " + " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        cwd=cwd,
    )
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            print("  " + line)
    proc.wait()
    return proc.returncode


def build_launcher_exe():
    header("STEP 1/3 - Building the launcher (SmartAssignmentChecker.exe)")
    launcher_src = os.path.join(PROJECT_ROOT, LAUNCHER_SRC)
    if not os.path.isfile(launcher_src):
        sys.exit(f"Missing launcher source: {launcher_src}")
    if not ensure_pyinstaller():
        sys.exit("Could not install PyInstaller.")

    rc = run([
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "SmartAssignmentChecker",
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        launcher_src,
    ])
    if rc != 0:
        sys.exit("PyInstaller failed to build the launcher - see output above.")

    if not os.path.isfile(LAUNCHER_OUTPUT_PATH):
        sys.exit("SmartAssignmentChecker.exe was not produced.")
    size_mb = round(os.path.getsize(LAUNCHER_OUTPUT_PATH) / (1024 * 1024), 1)
    print(f"Launcher created: {LAUNCHER_OUTPUT_PATH} ({size_mb} MB)")


def build_source_package():
    header("STEP 2/3 - Packaging the project source")
    for f in SOURCE_TOP_FILES:
        if not os.path.isfile(os.path.join(PROJECT_ROOT, f)):
            sys.exit(f"Missing required file: {f}")

    os.makedirs(DIST_DIR, exist_ok=True)
    if os.path.exists(SOURCE_ZIP_PATH):
        os.remove(SOURCE_ZIP_PATH)

    added = 0
    with zipfile.ZipFile(SOURCE_ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in SOURCE_TOP_FILES:
            zf.write(os.path.join(PROJECT_ROOT, f), arcname=f)
            print(f"  + {f}")
            added += 1

        for pkg in SOURCE_PACKAGES:
            pkg_dir = os.path.join(PROJECT_ROOT, pkg)
            if not os.path.isdir(pkg_dir):
                print(f"  ! skipping missing folder: {pkg}")
                continue
            for root, _dirs, files in os.walk(pkg_dir):
                for file in files:
                    full = os.path.join(root, file)
                    rel = os.path.relpath(full, PROJECT_ROOT)
                    zf.write(full, arcname=rel)
                    added += 1

        zf.write(LAUNCHER_OUTPUT_PATH, arcname=LAUNCHER_EXE)
        print(f"  + {LAUNCHER_EXE}")
        zf.writestr(DEPS_SCRIPT, DEPS_SCRIPT_CONTENT)
        print(f"  + {DEPS_SCRIPT}")

    size_mb = round(os.path.getsize(SOURCE_ZIP_PATH) / (1024 * 1024), 1)
    print(f"Packaged {added} source files -> {SOURCE_ZIP_PATH} ({size_mb} MB)")


def build_setup_exe():
    header("STEP 3/3 - Compiling the installer (setup.exe)")
    installer_path = os.path.join(PROJECT_ROOT, INSTALLER_SCRIPT)
    if not os.path.isfile(installer_path):
        sys.exit(f"Missing installer script: {installer_path}")
    if not ensure_pyinstaller():
        sys.exit("Could not install PyInstaller.")

    sep = os.pathsep
    rc = run([
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--name", "setup",
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--add-data", f"{SOURCE_ZIP_PATH}{sep}.",
        INSTALLER_SCRIPT,
    ])
    if rc != 0:
        sys.exit("PyInstaller failed to build setup.exe - see output above.")

    if not os.path.isfile(SETUP_OUTPUT_PATH):
        sys.exit("setup.exe was not produced.")
    size_mb = round(os.path.getsize(SETUP_OUTPUT_PATH) / (1024 * 1024), 1)
    print(f"Setup created: {SETUP_OUTPUT_PATH} ({size_mb} MB)")


def summary():
    header("DONE - Setup ready to distribute")
    print(f"  Launcher       : {LAUNCHER_OUTPUT_PATH}")
    print(f"  Source package : {SOURCE_ZIP_PATH}")
    print(f"  Installer      : {SETUP_OUTPUT_PATH}")
    print("\n  Share `dist/setup.exe` on your site. Users run it to install the project.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        print("Cleaning previous build artifacts...")
        if os.path.isdir(BUILD_DIR):
            shutil.rmtree(BUILD_DIR, ignore_errors=True)
    build_launcher_exe()
    build_source_package()
    build_setup_exe()
    summary()


if __name__ == "__main__":
    main()