@echo off
set SCRIPT_DIR=%~dp0
set VENV=%SCRIPT_DIR%.venv

if not exist "%VENV%\Scripts\python.exe" (
    echo Setting up virtual environment...
    python -m venv "%VENV%"
    "%VENV%\Scripts\pip" install -q -e "%SCRIPT_DIR%[pretty]"
    echo Setup complete.
)

"%VENV%\Scripts\python" -m hb_downloader --links "%SCRIPT_DIR%links.txt" --config "%SCRIPT_DIR%config.toml" --output "%SCRIPT_DIR%downloads"
pause
