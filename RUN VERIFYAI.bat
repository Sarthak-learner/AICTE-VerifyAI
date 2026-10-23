
@echo off
title AICTE VerifyAI Launcher
cd /d D:\SIH

echo ========================================
echo       AICTE VerifyAI Launcher
echo ========================================

echo Checking backend on port 8001...
powershell -NoProfile -Command "try { $r=Invoke-RestMethod 'http://127.0.0.1:8001/api/v1/health' -TimeoutSec 3; if ($r.status -eq 'ok' -and $r.database -eq 'ok') { exit 0 } else { exit 1 } } catch { exit 1 }"

if %errorlevel%==0 (
    echo Backend is already running.
) else (
    echo Starting backend...
    start "VerifyAI Backend" cmd /k "cd /d D:\SIH\backend && set DATABASE_URL=sqlite:///./verifyai.db && python -m uvicorn app.main:app --host 127.0.0.1 --port 8001"
)

echo Waiting for backend...
powershell -NoProfile -Command "$ok=$false; for($i=0;$i -lt 30;$i++){try{$r=Invoke-RestMethod 'http://127.0.0.1:8001/api/v1/health' -TimeoutSec 2;if($r.status -eq 'ok' -and $r.database -eq 'ok'){$ok=$true;break}}catch{};Start-Sleep -Seconds 1};if(-not $ok){exit 1}"

if errorlevel 1 (
    echo ERROR: Backend did not become healthy on port 8001.
    pause
    exit /b 1
)

echo Starting frontend...
start "VerifyAI Frontend" cmd /k "cd /d D:\SIH\frontend && npm run dev -- --host 127.0.0.1"

echo Waiting for frontend...
powershell -NoProfile -Command "$ok=$false; for($i=0;$i -lt 30;$i++){try{$r=Invoke-WebRequest 'http://127.0.0.1:5173' -TimeoutSec 2;if($r.StatusCode -eq 200){$ok=$true;break}}catch{};Start-Sleep -Seconds 1};if(-not $ok){exit 1}"

if errorlevel 1 (
    echo WARNING: Frontend did not respond on port 5173.
    echo Check the VerifyAI Frontend window.
    pause
    exit /b 1
)

start "" "http://localhost:5173"
echo AICTE VerifyAI is ready!
exit /b 0
