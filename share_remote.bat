@echo off
echo ===================================================
echo     STARTING REMOTE SHARING (Simplified)
echo ===================================================
echo.
echo NOTE: Ensure you have run 'ngrok config add-authtoken YOUR_TOKEN' at least once!
echo.
echo ---------------------------------------------------
echo 1. I am opening ONE window.
echo 2. COPY the URL (e.g., https://...ngrok-free.app).
echo 3. SHARE that link with your friends.
echo 4. IMPORTANT: They should put the SAME link in Settings!
echo ---------------------------------------------------
echo.

echo Starting Unified Tunnel (Port 8000)...
start "Unified Tunnel (SHARE THIS LINK)" cmd /k "ngrok http 8000"

echo.
echo Done! Checking window...
pause
