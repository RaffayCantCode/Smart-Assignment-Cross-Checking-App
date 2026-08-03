import os
import sys
import subprocess
import shutil

def main():
    print("============================================================")
    # 1. Run build_exe.bat to build the application and generate the ZIP package
    print("Step 1: Running build_exe.bat to compile main application...")
    print("============================================================")
    
    # We will invoke build_exe.bat and wait for completion
    try:
        # Running build_exe.bat directly
        process = subprocess.run(["build_exe.bat"], shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: build_exe.bat failed with exit code {e.returncode}")
        sys.exit(1)

    zip_file = os.path.join("dist", "SmartAssignmentChecker-App.zip")
    if not os.path.exists(zip_file):
        print(f"Error: build_exe.bat succeeded but did not produce {zip_file}")
        sys.exit(1)

    print("\n============================================================")
    print("Step 2: Compiling installer.py using PyInstaller...")
    print("============================================================")
    
    # Determine python path
    py_executable = sys.executable
    print(f"Using Python interpreter: {py_executable}")
    
    # We compile installer.py to a single exe named 'setup.exe'
    # and bundle 'dist/SmartAssignmentChecker-App.zip' inside it.
    pyinstaller_cmd = [
        py_executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--add-data", f"dist/SmartAssignmentChecker-App.zip{os.pathsep}.",
        "--name", "setup",
        "installer.py"
    ]
    
    print(f"Running command: {' '.join(pyinstaller_cmd)}")
    try:
        subprocess.run(pyinstaller_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: PyInstaller compilation of setup.exe failed.")
        sys.exit(1)

    # 3. Copy the compiled setup.exe from dist/ to the project root directory
    compiled_exe = os.path.join("dist", "setup.exe")
    if os.path.exists(compiled_exe):
        shutil.copy(compiled_exe, ".")
        print("\n============================================================")
        print(" SUCCESS: setup.exe has been compiled and placed in the project root!")
        print(f" Location: {os.path.abspath('setup.exe')}")
        print("============================================================")
    else:
        print(f"Error: setup.exe was not found in 'dist/' after PyInstaller ran.")
        sys.exit(1)

if __name__ == "__main__":
    main()
