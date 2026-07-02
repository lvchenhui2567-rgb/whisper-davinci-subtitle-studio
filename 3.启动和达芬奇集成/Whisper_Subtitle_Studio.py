#!/usr/bin/env python
import os
import runpy

ffmpeg_dir = r"D:\WhisperWebUI整合包\2.whisper+ffmpeg安装\ffmpeg\bin"
if os.path.exists(ffmpeg_dir):
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

runpy.run_path(r"D:\WhisperDaVinci字幕工作站整合包\3.启动和达芬奇集成\WhisperSubtitleStudio\davinci_whisper_subtitle_studio.py", run_name="__main__")
