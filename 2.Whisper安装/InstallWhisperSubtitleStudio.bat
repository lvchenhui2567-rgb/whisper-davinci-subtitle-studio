@echo off
setlocal

set "APP_DIR=%~dp0..\3.启动和达芬奇集成\WhisperSubtitleStudio"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Run Step 1 first.
  pause
  exit /b 1
)

if not exist "%APP_DIR%\davinci_whisper_subtitle_studio.py" (
  echo [ERROR] App folder not found: %APP_DIR%
  pause
  exit /b 1
)

if not exist "%APP_DIR%\.venv\Scripts\python.exe" (
  echo Creating local .venv...
  python -m venv "%APP_DIR%\.venv"
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv.
    pause
    exit /b 1
  )
)

echo Installing Whisper runtime into local .venv...
"%APP_DIR%\.venv\Scripts\python.exe" -m pip install -U pip openai-whisper faster-whisper
if errorlevel 1 (
  echo [ERROR] Dependency install failed.
  pause
  exit /b 1
)

"%APP_DIR%\.venv\Scripts\python.exe" -c "import whisper; import faster_whisper; print('Whisper runtime OK')"
if errorlevel 1 (
  echo [ERROR] Import check failed.
  pause
  exit /b 1
)

echo Install complete.
pause
