@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  build_exe.bat
REM
REM  Builds a standalone Windows .exe for the Smart Assignment
REM  Cross-Checking App using PyInstaller.
REM
REM  If Python isn't found on this machine, this script installs
REM  it for you automatically before continuing.
REM
REM  Run this ON WINDOWS, from inside the SmartAssignmentChecker
REM  folder (the one containing main.py). Double-click it, or
REM  run it from a command prompt: build_exe.bat
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

REM --- 3. Not found anywhere: install it automatically ---------------------
echo.
echo Python was not found on this computer. Installing it now...
echo (This only happens once - future runs will skip this step.)
echo.

where winget >nul 2>nul
if %errorlevel%==0 (
    echo Installing Python via winget, this can take a few minutes...
    winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo winget install did not succeed, will try direct download instead...
        goto :download_installer
    )
    goto :post_install_search
)

:download_installer
echo Downloading the official Python installer...
set "PYINSTALLER_URL=https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
set "PYINSTALLER_FILE=%TEMP%\python-installer.exe"
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PYINSTALLER_URL%' -OutFile '%PYINSTALLER_FILE%'"
if not exist "%PYINSTALLER_FILE%" (
    echo.
    echo ============================================================
    echo  ERROR: Could not download the Python installer. This
    echo  usually means there's no internet connection, or a
    echo  firewall is blocking it.
    echo.
    echo  Manual fix: go to https://www.python.org/downloads/,
    echo  install it yourself with "Add python.exe to PATH" checked,
    echo  then run this script again.
    echo ============================================================
    pause
    exit /b 1
)

echo Running installer silently ^(this takes a minute^)...
"%PYINSTALLER_FILE%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1
del "%PYINSTALLER_FILE%" >nul 2>nul

:post_install_search
REM PATH changes made by the installer aren't visible to this already-running
REM script, so we search the disk directly for the python.exe that was just installed.
set "PYEXE="
call :search_common_paths
if defined PYEXE goto :found

echo.
echo ============================================================
echo  ERROR: Python was installed but this script couldn't locate
echo  it automatically. Please close this window, reopen a new
echo  Command Prompt, and run build_exe.bat again - the new
echo  window will be able to see it.
echo ============================================================
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
echo Installing/upgrading dependencies (this can take a minute)...
"%PYEXE%" -m pip install --upgrade pip
"%PYEXE%" -m pip install -r requirements.txt
"%PYEXE%" -m pip install pyinstaller

if %errorlevel% neq 0 (
    echo.
    echo ERROR: pip install failed. Scroll up to see what went wrong.
    pause
    exit /b 1
)

echo.
echo Building executable...
"%PYEXE%" -m PyInstaller --noconfirm --onefile --windowed ^
    --name "SmartAssignmentChecker" ^
    --add-data "assets;assets" ^
    main.py

if not exist "dist\SmartAssignmentChecker.exe" (
    echo.
    echo ============================================================
    echo  ERROR: The build did not produce an .exe. Scroll up in this
    echo  window to find the actual error message from PyInstaller -
    echo  that's the part that matters, everything above it is setup.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  SUCCESS! Your .exe is here:
echo     dist\SmartAssignmentChecker.exe
echo ============================================================
echo.
pause
