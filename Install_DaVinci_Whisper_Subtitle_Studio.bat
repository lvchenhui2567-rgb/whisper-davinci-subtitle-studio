@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1

where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3.10+ first.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 (
    echo Failed to create .venv.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -m pip install -U pip openai-whisper faster-whisper
if errorlevel 1 (
  echo Dependency install failed.
  pause
  exit /b 1
)

if not exist "models\large-v3-turbo.pt" (
  if exist "D:\WhisperWebUI整合包\2.whisper+ffmpeg安装\models\large-v3-turbo.pt" (
    copy /Y "D:\WhisperWebUI整合包\2.whisper+ffmpeg安装\models\large-v3-turbo.pt" "models\large-v3-turbo.pt" >nul
  )
)

".venv\Scripts\python.exe" -c "import whisper; import faster_whisper; print('Whisper deps OK')"
pause
