@echo off
setlocal
set "APP_DIR=%~dp0"
set "CODEX_PY=C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%CODEX_PY%" (
  set "BOOTSTRAP_PY=%CODEX_PY%"
) else (
  set "BOOTSTRAP_PY=python"
)

if not exist "%APP_DIR%.venv-build\Scripts\python.exe" (
  "%BOOTSTRAP_PY%" -m venv "%APP_DIR%.venv-build"
)

"%APP_DIR%.venv-build\Scripts\python.exe" -m pip install -r "%APP_DIR%requirements-build.txt"

"%APP_DIR%.venv-build\Scripts\python.exe" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --console ^
  --name linematcher ^
  --distpath "%APP_DIR%dist" ^
  --workpath "%APP_DIR%build\pyinstaller" ^
  --specpath "%APP_DIR%build" ^
  "%APP_DIR%match_cities.py"

if errorlevel 1 exit /b %errorlevel%
copy /Y "%APP_DIR%dist\linematcher.exe" "%APP_DIR%linematcher.exe" >nul
echo.
echo Built: %APP_DIR%dist\linematcher.exe
echo Synced: %APP_DIR%linematcher.exe
