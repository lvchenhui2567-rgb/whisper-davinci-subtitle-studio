@echo off
setlocal

set "SRC=%~dp0Whisper_Subtitle_Studio.py"
set "DST_DIR=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
set "DST=%DST_DIR%\Whisper_Subtitle_Studio.py"

if not exist "%SRC%" (
  echo Bridge file not found.
  pause
  exit /b 1
)

if not exist "%DST_DIR%" mkdir "%DST_DIR%"
copy /Y "%SRC%" "%DST%" >nul

echo Installed DaVinci menu entry:
echo %DST%
echo Restart DaVinci Resolve, then open Workspace ^> Scripts ^> Utility ^> Whisper_Subtitle_Studio
pause
