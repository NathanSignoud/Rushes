@echo off
rem Une nuit complete : simulation, episodes, puis voix des episodes qui n'en ont pas (SPEC 20.2).
rem Usage : scripts\nuit.bat [jours] [provider]      ex. : scripts\nuit.bat 2 groq
rem Une etape dont la commande n'existe pas encore (phase pas atteinte) est sautee.
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0.."
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
set "JOURS=%~1"
if "%JOURS%"=="" set "JOURS=2"
set "PROVIDER="
if not "%~2"=="" set "PROVIDER=--provider %~2"

call :etape simulate --jours %JOURS% %PROVIDER% || goto :fin
call :etape episode %PROVIDER% || goto :fin
call :disponible audio && (
  for %%f in (data\episodes\ep*.json) do (
    if not exist "data\episodes\%%~nf.mp3" (
      set "N=%%~nf"
      call :etape audio --episode !N:ep=! || goto :fin
    )
  )
)
echo.
echo Nuit terminée.
goto :fin

:disponible
"%PY%" -m rushes %1 --help >nul 2>&1
if errorlevel 1 (
  echo [étape sautée] La commande « %1 » n'existe pas encore.
  exit /b 1
)
exit /b 0

:etape
call :disponible %1 || exit /b 0
echo.
echo === python -m rushes %* ===
"%PY%" -m rushes %*
exit /b %errorlevel%

:fin
endlocal
