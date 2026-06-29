@echo off
REM Quick Start: CIS Local Prototype (Windows)

setlocal enabledelayedexpansion

echo === CIS Quick Start ^(Prototype Mode, Windows^) ===
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: python not found. Install Python 3.10+ and try again.
    exit /b 1
)

cd /d "%~dp0cis"

echo 📦 Setting up Python environment...
python -m venv .venv
call .venv\Scripts\activate.bat

echo 📚 Installing dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo 🧠 Training model...
python train.py --epochs 1 --save models/lstm_gnn_scripted.pt

echo.
echo ✅ Setup complete!
echo.
echo To run the unified service ^(in one terminal^):
echo   cd ..
echo   .venv\Scripts\activate
echo   python -m cis.service
echo.
echo To inject test events ^(in another terminal^):
echo   cd cis
echo   .venv\Scripts\activate
echo   python simulate_events.py
echo.
echo To monitor alerts in real-time:
echo   type \tmp\cis_alerts.jsonl
echo.
