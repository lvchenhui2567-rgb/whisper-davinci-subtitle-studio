@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1

if exist "D:\WhisperWebUI整合包\2.whisper+ffmpeg安装\ffmpeg\bin\ffmpeg.exe" (
  set "PATH=D:\WhisperWebUI整合包\2.whisper+ffmpeg安装\ffmpeg\bin;%PATH%"
)

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "davinci_whisper_subtitle_studio.py"
) else (
  python "davinci_whisper_subtitle_studio.py"
)

pause
