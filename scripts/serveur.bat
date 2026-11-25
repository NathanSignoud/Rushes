@echo off
rem Interface web ouverte au reseau local, pour un telephone sur le meme Wi-Fi (SPEC 20.3).
rem Usage : scripts\serveur.bat [port]
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
set "PORT=%~1"
if "%PORT%"=="" set "PORT=8000"

"%PY%" -m rushes serve --help >nul 2>&1
if errorlevel 1 (
  echo La commande « serve » n'existe pas encore ^(phase 4^).
  exit /b 1
)
echo Sur le téléphone ^(même Wi-Fi^), ouvrez l'une de ces adresses :
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
  for /f "tokens=*" %%b in ("%%a") do echo   http://%%b:%PORT%
)
echo Au premier lancement, autorisez Python dans le pare-feu pour les réseaux privés uniquement.
echo Ctrl+C pour arrêter.
echo.
"%PY%" -m rushes serve --host 0.0.0.0 --port %PORT%
endlocal
