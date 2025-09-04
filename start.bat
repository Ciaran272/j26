@echo off
echo Japanese Furigana Generator
echo ================================
echo.

echo Step 1: Check Python...
python --version
if errorlevel 1 (
    echo Error: Python not found
    pause
    exit /b 1
)
echo Python OK ✓
echo.

echo Step 2: Check virtual environment...
if exist .venv (
    echo Virtual env exists, activating...
    call .venv\Scripts\activate.bat
    if errorlevel 1 (
        echo Error: Failed to activate
        pause
        exit /b 1
    )
    echo Virtual env activated ✓
) else (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Error: Failed to create
        pause
        exit /b 1
    )
    echo Virtual env created ✓
    
    echo Activating...
    call .venv\Scripts\activate.bat
    if errorlevel 1 (
        echo Error: Failed to activate
        pause
        exit /b 1
    )
    echo Virtual env activated ✓
    
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install
        pause
        exit /b 1
    )
    echo Dependencies installed ✓
)
echo.

echo Step 3: Start server...
echo Server: http://127.0.0.1:5000
echo Press Ctrl+C to stop
echo.
python server.py

echo.
echo Server stopped, press any key...
pause



