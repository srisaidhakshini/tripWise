@echo off
setlocal
cd /d "%~dp0"

set "PORT=8011"
set "TRIPWISE_DB=%~dp0tripwise.db"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.10 or newer, then run this file again.
  pause
  exit /b 1
)

echo Starting the latest TripWise server at http://127.0.0.1:%PORT%/
echo Keep this window open while using TripWise. Server messages will appear here.
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:%PORT%/'"
python -u server.py

echo.
echo TripWise has stopped. Press any key to close this window.
pause >nul
