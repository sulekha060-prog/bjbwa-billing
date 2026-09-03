@echo off
title Basant Jamini Bhawan - Billing Automation Hub Web
cd /d "%~dp0\backend"

echo =========================================================================
echo  Basant Jamini Bhawan Welfare Association - Automation Hub (Web App)
echo =========================================================================
echo.
echo Starting web server at http://127.0.0.1:8000 ...
echo Press Ctrl+C to stop the server at any time.
echo.

start "" "http://127.0.0.1:8000"
py -m uvicorn app:app --host 127.0.0.1 --port 8000

pause
