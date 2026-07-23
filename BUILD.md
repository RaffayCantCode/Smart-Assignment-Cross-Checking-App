# Building a Windows .exe

PyInstaller (the tool that does this) has to run **on the same OS you're
targeting** — it can't cross-compile a Windows .exe from Linux/Mac. So this
step has to happen on a Windows machine (yours, a lab PC, whatever you'll
demo from).

## Quick way

1. Double-click `build_exe.bat` (or run it from Command Prompt).
   - If Python or dependencies aren't installed, the script handles setup.
2. Wait for it to finish (~1 minute).
3. Your application folder is produced at `dist\SmartAssignmentChecker\`.
   - Main binary: `dist\SmartAssignmentChecker\SmartAssignmentChecker.exe`
   - All required `.dll` files, Python runtime, and libraries are included inside this folder.
   - Distribution archive: `dist\SmartAssignmentChecker-App.zip` (ready to copy/share for presentations).

## Manual way

```bat
pip install -r requirements.txt
pip install pyinstaller
pyinstaller SmartAssignmentChecker.spec --noconfirm
```

- `--onefile` → bundles everything into a single .exe (bigger, slightly
  slower to start, but way easier to hand someone).
- `--windowed` → suppresses the black console window behind the GUI.
- `--add-data "assets;assets"` → bundles the assets folder in (harmless
  even though it's currently empty — future icons/images will need it).

## If you want a custom icon

Drop a `.ico` file at `assets/icons/app_icon.ico`, then add
`--icon=assets\icons\app_icon.ico` to the PyInstaller command (or edit
`build_exe.bat`).

## About the auto-install step

`build_exe.bat` first checks if Python is already on your PATH, then
checks common install folders in case it's installed but just wasn't
added to PATH. Only if neither finds anything does it install Python
itself — silently, using `winget` (built into Windows 10/11) when
available, or by downloading the official installer from python.org
otherwise. This only happens once; on later runs it finds the Python it
already installed and skips straight to building.

## Common gotchas

- **Antivirus false positive** — PyInstaller onefile exes get flagged by
  some antivirus/SmartScreen as unrecognized software. It's a known
  false-positive pattern (unsigned + self-extracting), not an actual
  issue with this code. If it's a problem for your demo, use `--onedir`
  instead of `--onefile` (produces a folder instead of one file, but
  starts faster and triggers fewer AV warnings).
- **"Module not found" at runtime** — usually means the exe was built
  with a different PySide6 version than what's imported. Rerun
  `pip install -r requirements.txt` first.
- **Rebuilding after code changes** — just rerun `build_exe.bat`. Delete
  the `build/` and `dist/` folders first if you want a totally clean
  build.

## Iterating after this

Once you're actively developing again, don't rebuild the exe every time —
just run `python main.py` directly like normal. Only rebuild the exe when
you actually need to hand someone a standalone copy (e.g. before a demo).
