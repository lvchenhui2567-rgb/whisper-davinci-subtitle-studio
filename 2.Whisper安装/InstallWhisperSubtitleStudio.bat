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

echo Installing DaVinci Python bridge modules into local .venv...
for /f "delims=" %%i in ('"%APP_DIR%\.venv\Scripts\python.exe" -c "import site; print(site.getsitepackages()[0])"') do set "SITE_PACKAGES=%%i"
if not exist "%SITE_PACKAGES%" (
  echo [ERROR] Cannot locate site-packages.
  pause
  exit /b 1
)
copy /Y "%APP_DIR%\DaVinci库文件\DaVinciResolveScript.py" "%SITE_PACKAGES%\DaVinciResolveScript.py" >nul
copy /Y "%APP_DIR%\DaVinci库文件\python_get_resolve.py" "%SITE_PACKAGES%\python_get_resolve.py" >nul
if errorlevel 1 (
  echo [ERROR] Failed to copy DaVinci bridge modules.
  pause
  exit /b 1
)

"%APP_DIR%\.venv\Scripts\python.exe" -c "import whisper; import faster_whisper; import DaVinciResolveScript; print('Whisper and DaVinci bridge OK')"
if errorlevel 1 (
  echo [ERROR] Import check failed.
  pause
  exit /b 1
)

echo Install complete.
pause
