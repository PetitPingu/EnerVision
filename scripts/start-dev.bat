@echo off
setlocal

set "ROOT=%~dp0..\"

echo Demarrage des services EnerVision en mode dev...
echo.

start "EnerVision - Core API" cmd /k "cd /d ""%ROOT%apps\core_api"" && python -m uvicorn presentation.api:app --reload --port 8001"

start "EnerVision - Prediction" cmd /k "cd /d ""%ROOT%apps\prediction"" && python -m uvicorn presentation.api:app --reload --port 8002"

start "EnerVision - Dashboard" cmd /k "cd /d ""%ROOT%apps\dashboard"" && npm run dev"

echo Services lances dans des fenetres separees :
echo   - Core API    : http://localhost:8001
echo   - Prediction  : http://localhost:8002
echo   - Dashboard   : http://localhost:3000
echo.
