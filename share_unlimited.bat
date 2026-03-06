@echo off
setlocal
echo ===================================================
echo     STARTING UNLIMITED GLOBAL SHARING 🌍
echo ===================================================
echo.
echo [1/3] Building Optimized Frontend...
cd frontend-app
cmd /c "npm run build"
cd ..

if not exist "frontend-app\dist\index.html" (
    echo.
    echo ❌ ERROR: Build failed. Check your Node.js installation.
    pause
    exit /b
)

echo.
echo [2/3] Fetching Tunnel Password (Public IP)...
for /f "delims=" %%a in ('powershell -command "Invoke-RestMethod -Uri 'https://api.ipify.org'"') do set "PUB_IP=%%a"
echo Public IP: %PUB_IP%

echo.
echo [3/3] Starting Unified Backend...
:: Start backend in a separate window
start "Unified Global Backend" cmd /k "uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo.
echo [4/4] Creating Global Tunnel...
echo.
echo ---------------------------------------------------
echo YOUR APP IS GOING GLOBAL!
echo ---------------------------------------------------
echo 1. Wait for the URL below (look for 'your url is: ...').
echo 2. SHARE that link with anyone.
echo 3. TUNNEL PASSWORD: %PUB_IP%
echo    (If the website asks for a password, enter the IP above)
echo 4. IMPORTANT: Tell them to open it in CHROME or SAFARI.
echo ---------------------------------------------------
echo.

:: Use npx localtunnel to create the tunnel
npx localtunnel --port 8000

echo.
echo Tunnel closed.
pause
