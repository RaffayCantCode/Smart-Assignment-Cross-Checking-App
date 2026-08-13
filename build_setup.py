import os
import sys
import zipfile
import shutil
import subprocess

"""
build_setup.py

Developer build script. Run this to produce a single shareable installer:

    python build_setup.py

The ONLY file it produces is dist/setup.exe. Ship that one file to anyone
who needs the app. When they run it, a wizard installs the complete
application (including the One-to-Many dashboard) onto their device, and
they launch it via the installed SmartAssignmentChecker.exe or the desktop
shortcut it creates.

What it does:

  0. VALIDATE - compiles every shipped Python file so a syntax error can
                never sneak into the installer.
  1. LAUNCHER - compiles launcher.py into SmartAssignmentChecker.exe, which
                starts the app with the installed Python. This lives in the
                build staging area - it is bundled into the installer and is
                never left behind in dist/.
  2. PACKAGE  - compresses the complete runnable project source (backend,
                gui, styles - including the One-to-Many dashboard - plus
                main.py and requirements.txt) together with that launcher exe
                into a source zip in the build staging area.
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
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")          # only setup.exe lands here
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")        # intermediate artifacts stay here
LAUNCHER_STAGE_DIR = os.path.join(BUILD_DIR, "launcher")
SOURCE_ZIP_PATH = os.path.join(BUILD_DIR, SOURCE_ZIP)  # embedded into setup.exe
SETUP_OUTPUT_PATH = os.path.join(DIST_DIR, SETUP_EXE)
LAUNCHER_OUTPUT_PATH = os.path.join(LAUNCHER_STAGE_DIR, LAUNCHER_EXE)

SOURCE_TOP_FILES = ["main.py", "requirements.txt"]
SOURCE_PACKAGES = ["backend", "gui", "styles"]

# Folders / files that are never shipped inside the source package.
EXCLUDED_DIRS = {"__pycache__", ".git", ".idea", ".vscode"}
EXCLUDED_EXTENSIONS = {".pyc", ".pyo"}


def iter_ship_files():
    """Yield (absolute_src, archive_arcname) for every file that ships."""
    for name in SOURCE_TOP_FILES:
        yield os.path.join(PROJECT_ROOT, name), name

    for pkg in SOURCE_PACKAGES:
        pkg_dir = os.path.join(PROJECT_ROOT, pkg)
        if not os.path.isdir(pkg_dir):
            print(f"  ! skipping missing folder: {pkg}")
            continue
        for root, dirs, files in os.walk(pkg_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            for file in files:
                if os.path.splitext(file)[1].lower() in EXCLUDED_EXTENSIONS:
                    continue
                full = os.path.join(root, file)
                rel = os.path.relpath(full, PROJECT_ROOT)
                yield full, rel


def validate_sources():
    """Byte-compile every shipped .py so the setup can never contain
    syntactically broken code (e.g. an unfinished edit)."""
    header("STEP 0/4 - Validating shipped Python sources")
    errors = []
    count = 0
    for src, arc in iter_ship_files():
        if not src.lower().endswith(".py"):
            continue
        count += 1
        try:
            with open(src, "r", encoding="utf-8") as fh:
                compile(fh.read(), arc, "exec")
        except SyntaxError as e:
            errors.append(f"  ! {arc} (line {e.lineno}): {e.msg}")
    if errors:
        print("\n".join(errors))
        sys.exit("Source validation FAILED - fix the errors above before building.")
    print(f"  {count} Python files checked - all OK.")


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
    header("STEP 1/4 - Building the launcher (SmartAssignmentChecker.exe)")
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
        "--distpath", LAUNCHER_STAGE_DIR,
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
    header("STEP 2/4 - Packaging the project source")
    missing = [
        f for f in SOURCE_TOP_FILES
        if not os.path.isfile(os.path.join(PROJECT_ROOT, f))
    ]
    if missing:
        sys.exit(f"Missing required file(s): {', '.join(missing)}")

    os.makedirs(os.path.dirname(SOURCE_ZIP_PATH), exist_ok=True)
    if os.path.exists(SOURCE_ZIP_PATH):
        os.remove(SOURCE_ZIP_PATH)

    added = 0
    with zipfile.ZipFile(SOURCE_ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for src, arc in iter_ship_files():
            zf.write(src, arcname=arc)
            print(f"  + {arc}")
            added += 1

        zf.write(LAUNCHER_OUTPUT_PATH, arcname=LAUNCHER_EXE)
        print(f"  + {LAUNCHER_EXE}")
        zf.writestr(DEPS_SCRIPT, DEPS_SCRIPT_CONTENT)
        print(f"  + {DEPS_SCRIPT}")

    size_mb = round(os.path.getsize(SOURCE_ZIP_PATH) / (1024 * 1024), 1)
    print(f"Packaged {added} source files -> {SOURCE_ZIP_PATH} ({size_mb} MB)")


def build_setup_exe():
    header("STEP 3/4 - Compiling the installer (setup.exe)")
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
    size_mb = round(os.path.getsize(SETUP_OUTPUT_PATH) / (1024 * 1024), 1)
    print(f"  Installer      : {SETUP_OUTPUT_PATH} ({size_mb} MB)")
    print("\n  `dist/` now contains exactly one file to share: setup.exe")
    print("  It embeds the full application (including the One-to-Many dashboard).")
    print("  Users run setup.exe, the wizard installs the app, and they launch it")
    print("  from the installed SmartAssignmentChecker.exe / desktop shortcut.")


def remove_stale_dist_artifacts():
    """Make sure dist/ only ever contains setup.exe (drop leftovers from
    older builds where the launcher exe and source zip were published)."""
    for stale in (LAUNCHER_EXE, SOURCE_ZIP):
        path = os.path.join(DIST_DIR, stale)
        if os.path.isfile(path):
            os.remove(path)
            print(f"  removed stale dist artifact: {stale}")


def clean_build_dir():
    """Remove the entire build/ staging area now that setup.exe is done."""
    if os.path.isdir(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
        print(f"  cleaned build folder: {BUILD_DIR}")
    else:
        print("  build folder already clean.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        print("Cleaning previous build artifacts...")
        if os.path.isdir(BUILD_DIR):
            shutil.rmtree(BUILD_DIR, ignore_errors=True)
    validate_sources()
    build_launcher_exe()
    build_source_package()
    build_setup_exe()
    remove_stale_dist_artifacts()
    clean_build_dir()
    summary()


if __name__ == "__main__":
    main()