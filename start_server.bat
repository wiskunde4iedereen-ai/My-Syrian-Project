@echo off
cd /d "%~dp0"
echo Starting Heya System Server...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
