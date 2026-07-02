Whisper DaVinci 字幕工作站整合包

1. 安装依赖
   运行：Install_DaVinci_Whisper_Subtitle_Studio.bat

2. 在 DaVinci 菜单中使用
   把下面这个文件复制到 DaVinci 的 Fusion Scripts Utility 目录：
   DaVinci菜单入口\Whisper_Subtitle_Studio.py

   目标目录通常是：
   C:\Users\TSJ-010\AppData\Roaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility

3. 启动位置
   DaVinci Resolve 顶部菜单：Workspace -> Scripts -> Whisper_Subtitle_Studio

4. 本地启动测试
   可运行：Start_DaVinci_Whisper_Subtitle_Studio.bat

5. 模型来源
   安装脚本会优先复制：
   D:\WhisperWebUI整合包\2.whisper+ffmpeg安装\models\large-v3-turbo.pt

   如果未复制成功，主脚本仍会尝试直接读取上面的原始模型路径。

6. 字幕替换注意
   脚本会删除当前时间线旧字幕，再尝试按旧字幕起点插入修正版 SRT。
   第一次使用建议先复制时间线测试。
