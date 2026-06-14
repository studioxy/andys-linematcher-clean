@echo off
setlocal
set "APP_DIR=%~dp0"
set "CODEX_PY=C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%APP_DIR%linematcher.exe" (
  if "%~1"=="" (
    "%APP_DIR%linematcher.exe"
  ) else (
    "%APP_DIR%linematcher.exe" %*
  )
  exit /b %errorlevel%
)

if exist "%APP_DIR%.venv\Scripts\python.exe" (
  set "PY=%APP_DIR%.venv\Scripts\python.exe"
) else if exist "%CODEX_PY%" (
  set "PY=%CODEX_PY%"
) else (
  set "PY=python"
)

if "%~1"=="" (
  "%PY%" "%APP_DIR%match_cities.py"
) else (
  "%PY%" "%APP_DIR%match_cities.py" %*
)
