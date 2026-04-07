@echo off
REM Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
REM
REM  Licensed under the Apache License, Version 2.0 (the "License");
REM  you may not use this file except in compliance with the License.
REM  You may obtain a copy of the License at
REM
REM      http://www.apache.org/licenses/LICENSE-2.0
REM
REM  Unless required by applicable law or agreed to in writing, software
REM  distributed under the License is distributed on an "AS IS" BASIS,
REM  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
REM  See the License for the specific language governing permissions and
REM  limitations under the License.

REM setup_qtest_env.bat - Set up qtest CLI tool on Windows
REM Usage: setup_qtest_env.bat

echo.
echo ============================================
echo   qtest CLI - Setup (Windows)
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: python not found. Install Python 3.8+ first.
    echo Download from https://www.python.org/downloads/
    exit /b 1
)

for /f "tokens=*" %%i in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PYTHON_VERSION=%%i
echo   Python version : %PYTHON_VERSION%
echo   Project dir    : %~dp0
echo.

REM Create venv
set VENV_DIR=%~dp0.venv

if exist "%VENV_DIR%" (
    echo [1/2] Virtual environment already exists
) else (
    echo [1/2] Creating virtual environment...
    python -m venv "%VENV_DIR%"
)

REM Activate and install
echo [2/2] Installing dependencies...
call "%VENV_DIR%\Scripts\activate.bat"
pip install --quiet --upgrade pip
pip install --quiet -e "%~dp0"

echo.
echo ============================================
echo   Setup complete!
echo ============================================
echo.
echo   Virtual env: %VENV_DIR%
echo.
echo   To activate the virtual environment:
echo     %VENV_DIR%\Scripts\activate.bat
echo.
echo   To deactivate:
echo     deactivate
echo.
echo   After activating, the 'qtest' command is available:
echo     qtest --help
echo     qtest ls
echo     qtest add-tc --dry-run
echo     qtest download "Omnia-2.X/Slurm Cluster"
echo.
echo   Next steps:
echo.
echo   1. Edit config.yaml with your qTest details
echo   2. Activate venv: %VENV_DIR%\Scripts\activate.bat
echo   3. Test: qtest ls
echo.
