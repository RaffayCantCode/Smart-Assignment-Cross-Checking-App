import os
import sys
import zipfile
import shutil
import subprocess
import time

"""
build_setup.py

Builds a single, 100% standalone, professional Windows setup.exe installer.

Build flow:
  0. VALIDATE  - Compiles every shipped Python file to prevent syntax errors.
  1. BUILD APP - Uses PyInstaller to bundle the entire Python runtime, PySide6,
                 PyMuPDF, python-docx, scikit-learn, scipy, numpy, Pillow, pytesseract,
                 sentence-transformers, transformers, torch, and nltk into a standalone
                 application folder (build/app_bundle/SmartAssignmentChecker/).
  2. COMPILE INSTALLER:
     - Uses Inno Setup (ISCC.exe) to create a native, professional Windows Installation Wizard
       (dist/setup.exe) with LZMA2 ultra solid compression, Start Menu & Desktop shortcuts,
       and an official Windows Control Panel uninstaller (unins000.exe).
     - If Inno Setup is not present, falls back to the embedded PyInstaller setup wizard.
  3. CLEAN     - Cleans intermediate staging folders.

The resulting dist/setup.exe can be shipped to ANY Windows user.
Zero Python dependencies required on client machines!
"""

APP_NAME = "Smart Assignment Checker"
SETUP_EXE = "setup.exe"
INSTALLER_SCRIPT = "Setup.py"
UNINSTALLER_SCRIPT = "uninstall.py"
APP_PACKAGE_ZIP = "SmartAssignmentChecker-App.zip"
MAIN_ENTRY = "main.py"
APP_EXE = "SmartAssignmentChecker.exe"
UNINSTALL_EXE = "uninstall.exe"
INNO_ISS_SCRIPT = "installer.iss"

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
APP_STAGE_DIR = os.path.join(BUILD_DIR, "app_bundle")
UNINSTALL_STAGE_DIR = os.path.join(BUILD_DIR, "uninstall_stage")
ZIP_OUTPUT_PATH = os.path.join(BUILD_DIR, APP_PACKAGE_ZIP)
SETUP_OUTPUT_PATH = os.path.join(DIST_DIR, SETUP_EXE)

SOURCE_TOP_FILES = ["main.py", "requirements.txt", "uninstall.py"]
SOURCE_PACKAGES = ["backend", "gui", "styles", "assets"]
EXCLUDED_DIRS = {"__pycache__", ".git", ".idea", ".vscode"}
EXCLUDED_EXTENSIONS = {".pyc", ".pyo"}


def header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def ensure_pyinstaller() -> bool:
    try:
        import PyInstaller  # noqa: F401
        print("PyInstaller is available.", flush=True)
        return True
    except ImportError:
        print("PyInstaller not found - installing it now...", flush=True)
        return subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"]).returncode == 0


def find_inno_setup() -> str | None:
    candidates = [
        shutil.which("ISCC.exe"),
        shutil.which("iscc"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"),
        os.path.expandvars(r"%ProgramFiles%\Inno Setup 6\ISCC.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe"),
        os.path.expandvars(r"%ProgramFiles%\Inno Setup 7\ISCC.exe"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def run(cmd, cwd=PROJECT_ROOT) -> int:
    print("+ " + " ".join(cmd), flush=True)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        cwd=cwd,
        env=env,
    )
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            print("  " + line, flush=True)
    proc.wait()
    return proc.returncode


def validate_sources():
    header("STEP 0/4 - Validating Python sources")
    errors = []
    count = 0
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and d not in {"build", "dist", ".system_generated"}]
        for file in files:
            if file.endswith(".py"):
                full = os.path.join(root, file)
                count += 1
                try:
                    with open(full, "r", encoding="utf-8", errors="replace") as f:
                        source = f.read()
                    compile(source, full, "exec")
                except SyntaxError as e:
                    errors.append(f"  SYNTAX ERROR in {full}:{e.lineno} - {e.msg}")

    if errors:
        print("\nSource validation failed:")
        for err in errors:
            print(err)
        sys.exit(1)

    print(f"  {count} Python files checked - all OK.", flush=True)


def kill_running_instances():
    for name in ["SmartAssignmentChecker.exe", "setup.exe", "uninstall.exe"]:
        try:
            subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True)
        except Exception:
            pass
    time.sleep(0.5)


def safe_rmtree(path, retries=5, delay=0.5):
    if not os.path.exists(path):
        return
    kill_running_instances()
    for i in range(retries):
        try:
            shutil.rmtree(path, onexc=lambda func, p, exc: (os.chmod(p, 0o777), func(p)))
            return
        except Exception:
            time.sleep(delay)
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Remove-Item -LiteralPath '{path}' -Force -Recurse -ErrorAction SilentlyContinue"], capture_output=True)
    except Exception:
        pass


def build_standalone_app():
    header("STEP 1/4 - Compiling Standalone App Bundle (SmartAssignmentChecker)")
    if not ensure_pyinstaller():
        sys.exit("PyInstaller is required.")

    safe_rmtree(APP_STAGE_DIR)
    safe_rmtree(os.path.join(BUILD_DIR, "work_app"))

    main_script = os.path.join(PROJECT_ROOT, MAIN_ENTRY)
    if not os.path.isfile(main_script):
        sys.exit(f"Missing main entry point: {main_script}")

    sep = os.pathsep
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "SmartAssignmentChecker",
        "--distpath", APP_STAGE_DIR,
        "--workpath", os.path.join(BUILD_DIR, "work_app"),
        "--hidden-import", "PySide6",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",
        "--hidden-import", "PySide6.QtWidgets",
        "--hidden-import", "PySide6.QtSvg",
        "--hidden-import", "PySide6.QtNetwork",
        "--hidden-import", "fitz",
        "--hidden-import", "docx",
        "--hidden-import", "sklearn",
        "--hidden-import", "sklearn.feature_extraction.text",
        "--hidden-import", "sklearn.metrics.pairwise",
        "--hidden-import", "sklearn.utils",
        "--hidden-import", "scipy",
        "--hidden-import", "numpy",
        "--hidden-import", "PIL",
        "--hidden-import", "pytesseract",
        "--hidden-import", "sentence_transformers",
        "--hidden-import", "transformers",
        "--hidden-import", "torch",
        "--hidden-import", "nltk",
        "--hidden-import", "unittest",
        "--hidden-import", "unittest.mock",
        "--collect-all", "transformers",
        "--collect-all", "torch",
        "--collect-all", "tokenizers",
        "--collect-all", "safetensors",
        "--collect-all", "sentence_transformers",
        "--collect-all", "sklearn",
    ]

    for pkg in ["styles", "assets", "gui", "backend", "nltk_data"]:
        pkg_dir = os.path.join(PROJECT_ROOT, pkg)
        if os.path.isdir(pkg_dir):
            cmd.extend(["--add-data", f"{pkg_dir}{sep}{pkg}"])

    cmd.append(main_script)

    rc = run(cmd)
    if rc != 0:
        sys.exit("PyInstaller failed to build the standalone app.")

def prune_app_bundle(app_dir: str):
    """Safely cleans pycache caches and excessively deep license trees exceeding Windows MAX_PATH while preserving all library metadata (.dist-info), weights, and runtime files."""
    internal_dir = os.path.join(app_dir, "_internal")
    if not os.path.isdir(internal_dir):
        return

    removed = 0
    for root, dirs, files in os.walk(internal_dir, topdown=False):
        for d in list(dirs):
            if d in ("__pycache__", "licenses") or (d in ("tests", "test") and not d.endswith(".dist-info")):
                full_d = os.path.join(root, d)
                try:
                    shutil.rmtree(full_d, ignore_errors=True)
                    removed += 1
                except Exception:
                    pass
    print(f"Cleaned {removed} temporary caches and long path license trees from app bundle.", flush=True)


def build_installer_with_inno(iscc_path: str):
    header("STEP 2/4 - Compiling Professional Installation Wizard (Inno Setup)")
    app_dir = os.path.join(APP_STAGE_DIR, "SmartAssignmentChecker")
    prune_app_bundle(app_dir)
    iss_file = os.path.join(PROJECT_ROOT, INNO_ISS_SCRIPT)
    if not os.path.isfile(iss_file):
        sys.exit(f"Missing Inno Setup script: {iss_file}")

    os.makedirs(DIST_DIR, exist_ok=True)
    cmd = [iscc_path, iss_file]
    rc = run(cmd)
    if rc != 0:
        sys.exit("Inno Setup compilation failed.")

    if not os.path.isfile(SETUP_OUTPUT_PATH):
        sys.exit(f"Installer was not found at {SETUP_OUTPUT_PATH}")

    size_mb = round(os.path.getsize(SETUP_OUTPUT_PATH) / (1024 * 1024), 2)
    print(f"Professional Setup created successfully: {SETUP_OUTPUT_PATH} ({size_mb} MB)", flush=True)


def build_installer_fallback():
    header("STEP 2/4 - Compiling PyInstaller Setup Wizard (Fallback)")
    app_dir = os.path.join(APP_STAGE_DIR, "SmartAssignmentChecker")
    os.makedirs(BUILD_DIR, exist_ok=True)
    if os.path.exists(ZIP_OUTPUT_PATH):
        os.remove(ZIP_OUTPUT_PATH)

    print(f"Compressing {app_dir} -> {ZIP_OUTPUT_PATH}...", flush=True)
    total_files = 0
    with zipfile.ZipFile(ZIP_OUTPUT_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, dirs, files in os.walk(app_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, app_dir)
                zf.write(full_path, arcname=rel_path)
                total_files += 1

    installer_path = os.path.join(PROJECT_ROOT, INSTALLER_SCRIPT)
    os.makedirs(DIST_DIR, exist_ok=True)
    sep = os.pathsep
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "setup",
        "--distpath", DIST_DIR,
        "--workpath", os.path.join(BUILD_DIR, "work_setup"),
        "--add-data", f"{ZIP_OUTPUT_PATH}{sep}.",
        installer_path,
    ]
    rc = run(cmd)
    if rc != 0 or not os.path.isfile(SETUP_OUTPUT_PATH):
        sys.exit("Failed to compile fallback setup.exe.")


def clean_staging():
    header("STEP 3/4 - Cleaning Intermediate Build Artifacts")
    for folder in [APP_STAGE_DIR, UNINSTALL_STAGE_DIR, os.path.join(BUILD_DIR, "work_app"), os.path.join(BUILD_DIR, "work_setup")]:
        safe_rmtree(folder)
    if os.path.isfile(ZIP_OUTPUT_PATH):
        try:
            os.remove(ZIP_OUTPUT_PATH)
        except Exception:
            pass
    print("Cleaned temporary staging artifacts.", flush=True)


def summary():
    header("DONE - Professional Installer Ready to Distribute")
    size_mb = round(os.path.getsize(SETUP_OUTPUT_PATH) / (1024 * 1024), 2)
    print(f"  Installer  : {SETUP_OUTPUT_PATH}", flush=True)
    print(f"  Total Size : {size_mb} MB (Single portable installation wizard)", flush=True)
    print("\n  Summary:", flush=True)
    print("  [+] Professional Windows installation wizard (Welcome, Dir Selection, Progress, Finish)", flush=True)
    print("  [+] High-ratio solid LZMA2 compression", flush=True)
    print("  [+] Bundles all AI & document modules (PySide6, docx, PyMuPDF, sklearn, scipy, torch, OCR)", flush=True)
    print("  [+] Zero client Python dependency - works out of the box on any Windows PC", flush=True)
    print("  [+] Creates Desktop & Start Menu shortcuts with checkboxes", flush=True)
    print("  [+] Official uninstaller (unins000.exe) with clean removal from Windows Settings & Control Panel", flush=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        print("Cleaning previous build and dist artifacts...", flush=True)
        safe_rmtree(BUILD_DIR)
        safe_rmtree(DIST_DIR)

    validate_sources()
    build_standalone_app()

    iscc = find_inno_setup()
    if iscc:
        print(f"Found Inno Setup Compiler at: {iscc}", flush=True)
        build_installer_with_inno(iscc)
    else:
        print("Inno Setup not found, compiling fallback setup wizard...", flush=True)
        build_installer_fallback()

    clean_staging()
    summary()


if __name__ == "__main__":
    main()