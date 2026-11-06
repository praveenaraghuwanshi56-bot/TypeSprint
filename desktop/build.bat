@echo off
REM Builds ONE file: dist\TypeSprint.exe  (offline site + app + self-updater inside).
REM Needs Python 3.10+ (python.org, tick "Add to PATH"). Or skip this and let GitHub build it: see README-DESKTOP.md.
setlocal
cd /d "%~dp0"

echo [1/4] Preparing the offline website copy...
python tools\prepare_web.py || goto :fail

echo [2/4] Setting up Python packages (first run takes a few minutes)...
if not exist .venv ( python -m venv .venv || goto :fail )
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt || goto :fail

echo [3/4] Building TypeSprint.exe...
pyinstaller --noconfirm --clean --onefile --windowed --name TypeSprint --icon assets\icon.ico --paths src --add-data "src\web;web" src\main.py || goto :fail

echo [4/4] Checking the exe...
dist\TypeSprint.exe --selftest
if errorlevel 1 ( echo The built exe failed its self-check. & goto :fail )

echo.
echo DONE.  Give people this one file: dist\TypeSprint.exe
pause
exit /b 0

:fail
echo.
echo Build stopped because of the error above.
pause
exit /b 1
