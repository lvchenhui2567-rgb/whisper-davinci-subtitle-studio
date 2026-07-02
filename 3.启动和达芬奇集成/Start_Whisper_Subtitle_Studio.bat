@echo off
setlocal

set "APP_DIR=%~dp0WhisperSubtitleStudio"
set "PY=%APP_DIR%\.venv\Scripts\python.exe"

if exist "D:\WhisperWebUI整合包\2.whisper+ffmpeg安装\ffmpeg\bin\ffmpeg.exe" (
  set "PATH=D:\WhisperWebUI整合包\2.whisper+ffmpeg安装\ffmpeg\bin;%PATH%"
)

if exist "%PY%" (
  "%PY%" "%APP_DIR%\davinci_whisper_subtitle_studio.py"
) else (
  python "%APP_DIR%\davinci_whisper_subtitle_studio.py"
)

pause
