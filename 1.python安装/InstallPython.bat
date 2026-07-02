@echo off
setlocal

where python >nul 2>nul
if %errorlevel%==0 (
  python --version
  echo Python already exists. Skip install.
  pause
  exit /b 0
)

if not exist "%~dp0python-3.10.11-amd64.exe" (
  echo [ERROR] python-3.10.11-amd64.exe not found in this folder.
  echo Download Python 3.10.11 Windows installer and put it here, or install Python manually.
  pause
  exit /b 1
)

echo Installing Python 3.10.11 silently...
"%~dp0python-3.10.11-amd64.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1 SimpleInstall=1
if errorlevel 1 (
  echo [ERROR] Python install failed.
  pause
  exit /b 1
)

echo Python install finished. Reopen this BAT window if python is still not detected.
pause
