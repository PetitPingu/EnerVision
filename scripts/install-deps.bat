@echo off
setlocal

set "ROOT=%~dp0..\"

echo Installation des dependances EnerVision...
echo.

echo [1/3] Core API - pip install -r requirements.txt
cd /d "%ROOT%apps\core_api"
if errorlevel 1 (
    echo Erreur : impossible d'acceder au dossier core_api.
    exit /b 1
)
pip install -r requirements.txt
if errorlevel 1 (
    echo Erreur lors de l'installation des dependances Core API.
    exit /b 1
)
echo.

echo [2/3] Prediction - pip install -r requirements.txt
cd /d "%ROOT%apps\prediction"
if errorlevel 1 (
    echo Erreur : impossible d'acceder au dossier prediction.
    exit /b 1
)
pip install -r requirements.txt
if errorlevel 1 (
    echo Erreur lors de l'installation des dependances Prediction.
    exit /b 1
)
echo.

echo [3/4] Recommendation - pip install -r requirements.txt
cd /d "%ROOT%apps\recommendation"
if errorlevel 1 (
    echo Erreur : impossible d'acceder au dossier recommendation.
    exit /b 1
)
pip install -r requirements.txt
if errorlevel 1 (
    echo Erreur lors de l'installation des dependances Recommendation.
    exit /b 1
)
echo.

echo [4/4] Dashboard - npm install
cd /d "%ROOT%apps\dashboard"
if errorlevel 1 (
    echo Erreur : impossible d'acceder au dossier dashboard.
    exit /b 1
)
npm install
if errorlevel 1 (
    echo Erreur lors de l'installation des dependances Dashboard.
    exit /b 1
)
echo.

echo Installation terminee avec succes.
echo.
