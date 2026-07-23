@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  build_exe.bat
REM
REM  Builds a standalone Windows .exe for the Smart Assignment
REM  Cross-Checking App using PyInstaller.
REM  
REM  Make sure to run install_dependencies.bat first!
REM ============================================================

set "PYEXE="

echo Looking for Python...

REM --- 1. Already on PATH? -------------------------------------------------
where py >nul 2>nul
if %errorlevel%==0 (
    set "PYEXE=py"
    goto :found
)
where python >nul 2>nul
if %errorlevel%==0 (
    set "PYEXE=python"
    goto :found
)

REM --- 2. Installed already, just not on PATH? Search common locations ----
call :search_common_paths
if defined PYEXE goto :found

echo.
echo ERROR: Python was not found on this computer. 
echo Please run install_dependencies.bat first to install Python and dependencies.
echo.
pause
exit /b 1

:search_common_paths
for /d %%D in ("%LocalAppData%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
)
if defined PYEXE exit /b 0
for /d %%D in ("%ProgramFiles%\Python3*") do (
    if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
)
if defined PYEXE exit /b 0
for /d %%D in ("%ProgramFiles(x86)%\Python3*") do (
    if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
)
exit /b 0

:found
echo Using Python: %PYEXE%
"%PYEXE%" --version

echo.
echo Cleaning previous build artifacts...
if exist build rd /s /q build
if exist dist\SmartAssignmentChecker rd /s /q dist\SmartAssignmentChecker
if exist dist\SmartAssignmentChecker-App.zip del /q dist\SmartAssignmentChecker-App.zip

echo.
echo Building standalone executable folder using PyInstaller spec...
"%PYEXE%" -m PyInstaller SmartAssignmentChecker.spec --noconfirm

if not exist "dist\SmartAssignmentChecker\SmartAssignmentChecker.exe" (
    echo.
    echo ============================================================
    echo  ERROR: The build did not produce an .exe. Scroll up in this
    echo  window to find the actual error message from PyInstaller.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo Creating ZIP package for distribution...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\SmartAssignmentChecker\*' -DestinationPath 'dist\SmartAssignmentChecker-App.zip' -Force"

echo.
echo ============================================================
echo  SUCCESS! Your app folder and executable are ready:
echo     Folder: dist\SmartAssignmentChecker\
echo     Exe:    dist\SmartAssignmentChecker\SmartAssignmentChecker.exe
echo     Zip:    dist\SmartAssignmentChecker-App.zip
echo ============================================================
echo.
pause

