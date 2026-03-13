@echo off
rem ─────────────────────────────────────────────────────────────────────
rem  Databricks API Explorer — startup script (Windows)
rem ─────────────────────────────────────────────────────────────────────
setlocal enabledelayedexpansion

cd /d "%~dp0"

set VENV_DIR=.venv
set PORT=8050
if defined DATABRICKS_APP_PORT set PORT=%DATABRICKS_APP_PORT%

rem ── Find Python ─────────────────────────────────────────────────────
set PYTHON=
where python3 >nul 2>&1 && set PYTHON=python3
if not defined PYTHON (
    where python >nul 2>&1 && set PYTHON=python
)
if not defined PYTHON (
    echo ERROR: Python not found. Install Python 3.11+ and add it to PATH.
    pause
    exit /b 1
)

rem ── Check Python version ────────────────────────────────────────────
for /f "tokens=*" %%v in ('%PYTHON% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PY_VERSION=%%v
for /f "tokens=*" %%v in ('%PYTHON% -c "import sys; print(sys.version_info.major)"') do set PY_MAJOR=%%v
for /f "tokens=*" %%v in ('%PYTHON% -c "import sys; print(sys.version_info.minor)"') do set PY_MINOR=%%v

if !PY_MAJOR! lss 3 (
    echo ERROR: Python 3.11+ required ^(found %PY_VERSION%^).
    pause
    exit /b 1
)
if !PY_MAJOR! equ 3 if !PY_MINOR! lss 11 (
    echo ERROR: Python 3.11+ required ^(found %PY_VERSION%^).
    pause
    exit /b 1
)

echo Using Python %PY_VERSION%

rem ── Create virtual environment if missing ───────────────────────────
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Creating virtual environment...
    %PYTHON% -m venv %VENV_DIR%
)

rem ── Activate virtual environment ────────────────────────────────────
call %VENV_DIR%\Scripts\activate.bat

rem ── Install / update dependencies ───────────────────────────────────
echo Installing dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

rem ── Launch ──────────────────────────────────────────────────────────
echo.
echo Starting Databricks API Explorer on http://localhost:%PORT%
echo Press Ctrl+C to stop.
echo.
python app.py

pause
