@echo off
setlocal

REM 设置项目目录为批处理文件所在的目录
set "PROJ_DIR=%~dp0"

REM 检查Python是否安装
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8+ and add it to your PATH.
    pause
    exit /b 1
)

REM 设置虚拟环境的目录
set "VENV_DIR=%PROJ_DIR%venv"

REM 如果虚拟环境不存在，则创建它
if not exist "%VENV_DIR%\Scripts\activate" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM 激活虚拟环境并安装依赖
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