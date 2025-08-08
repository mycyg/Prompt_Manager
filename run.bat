@echo off
setlocal

REM Change the code page to UTF-8 to handle special characters in paths
chcp 65001 > nul

REM Set the project directory to the location of this batch file
set "PROJ_DIR=%~dp0"

REM Check for Python
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8+ and add it to your PATH.
    pause
    exit /b 1
)

REM Set the virtual environment directory
set "VENV_DIR=%PROJ_DIR%venv"

REM Create the virtual environment if it doesn't exist
if not exist "%VENV_DIR%\Scripts\activate" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate the virtual environment and install dependencies
echo Activating virtual environment and installing dependencies...
call "%VENV_DIR%\Scripts\activate.bat"

pip install -r "%PROJ_DIR%requirements.txt"
if %errorlevel% neq 0 (
    echo Failed to install requirements.
    pause
    exit /b 1
)

echo Starting the Prompt Manager application...
python "%PROJ_DIR%main.py"

endlocal
