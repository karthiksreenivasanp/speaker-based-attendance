@echo off
echo Starting Voice Attendance System...

:: Add Node.js to PATH (Temporary for this session)
set "PATH=C:\Program Files\nodejs;%PATH%"

:: Start Backend on 0.0.0.0
echo Getting Local IP...
ipconfig | findstr /i "IPv4"
start "Backend API" cmd /k "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait 3 seconds (Ping is more robust than timeout in some environments)
ping -n 4 127.0.0.1 >nul

:: Start Frontend (React)
cd frontend-app
start "Frontend PWA" cmd /k "call npm.cmd run dev -- --host"

echo System Started!
echo ---------------------------------------------------
echo [MOBILE ACCESS]
echo 1. Connect your phone to the SAME WiFi.
echo 2. Check the "Frontend PWA" window for the URL.
echo    It will look like: https://192.168.x.x:5173
echo.
echo    *** IMPORTANT: SELECT "ADVANCED" AND "PROCEED" TO BYPASS ***
echo    *** THE SELF-SIGNED CERTIFICATE WARNING ON YOUR PHONE.  ***
echo.
echo 3. Open that URL on your phone.
echo ---------------------------------------------------
echo Local Access: https://localhost:5173
echo Backend API:  http://localhost:8000
echo ---------------------------------------------------
