@echo off
echo Starting Sterling Stormwater...

:: ── Find available backend port (start at 8000) ──
set BACKEND_PORT=8000
:check_backend
netstat -ano | findstr /R /C:":%BACKEND_PORT% .*LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo Port %BACKEND_PORT% in use, trying next...
    set /a BACKEND_PORT+=1
    goto check_backend
)
echo Backend port: %BACKEND_PORT%

:: ── Find available frontend port (start at 8501) ──
set FRONTEND_PORT=8501
:check_frontend
netstat -ano | findstr /R /C:":%FRONTEND_PORT% .*LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo Port %FRONTEND_PORT% in use, trying next...
    set /a FRONTEND_PORT+=1
    goto check_frontend
)
echo Frontend port: %FRONTEND_PORT%

:: ── Launch both servers ──
start "Backend - FastAPI" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --port %BACKEND_PORT%"
timeout /t 2 /nobreak >nul
start "Frontend - Streamlit" cmd /k "cd /d %~dp0stormwater_app && python -m streamlit run app.py --server.port %FRONTEND_PORT%"

echo.
echo Both servers are starting...
echo Backend:  http://localhost:%BACKEND_PORT%/docs
echo Frontend: http://localhost:%FRONTEND_PORT%
echo.
pause
