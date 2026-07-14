Whisper DaVinci 字幕工作站整合包

使用顺序：

Step 1：安装 Python
打开文件夹：1.python安装
运行：InstallPython.bat
说明：如果电脑里已经能识别 python 命令，会自动跳过；否则需要把 Python 3.10.11 安装包放在这个文件夹后静默安装。

Step 2：安装 Whisper 运行环境
打开文件夹：2.Whisper安装
运行：InstallAll-Step2.bat
说明：会在本整合包的 WhisperSubtitleStudio 文件夹里创建独立 .venv，并把 Whisper 依赖安装到这个 .venv。
同时会把 DaVinciResolveScript.py、python_get_resolve.py 复制到这个 .venv 的 Python 库文件夹，确保外部 Python 能识别达芬奇脚本接口。
不会覆盖 VoxCPM2、IndexTTS 或全局 Python 环境。
这一步需要联网下载 Python 依赖。

Step 3A：本地启动测试
打开文件夹：3.启动和达芬奇集成
运行：Start_Whisper_Subtitle_Studio.bat

Step 3B：安装 DaVinci 菜单入口
打开文件夹：3.启动和达芬奇集成
运行：Install_DaVinci_Menu.bat
然后重启 DaVinci Resolve，在菜单里打开：
Workspace > Scripts > Utility > Whisper_Subtitle_Studio

本地 faster-whisper 模型位置：
3.启动和达芬奇集成\WhisperSubtitleStudio\large_v3_model
整合包本地版本已经放入 faster-whisper large-v3-turbo 模型。

openai-whisper .pt 模型兜底位置：
3.启动和达芬奇集成\WhisperSubtitleStudio\models\large-v3-turbo.pt

规则库位置：
3.启动和达芬奇集成\WhisperSubtitleStudio\srt_rules.json

DaVinci Python 桥接库位置：
3.启动和达芬奇集成\WhisperSubtitleStudio\DaVinci库文件

TXT 文稿导出：
在校对页点击“导出当前字幕为 TXT 文稿”，会把当前 SRT 中的序号和时间码去掉，只导出字幕正文。

注意事项：
- 不要改变整合包内部目录结构。
- 如果刚装完 Python，Step 2 里仍提示找不到 python，请关闭 BAT 窗口重新打开。
- 目标电脑如果有 NVIDIA 显卡，建议先安装或更新 NVIDIA 驱动。
- 当前安装脚本默认安装 pip 官方依赖；如需 CUDA 加速版 PyTorch，可后续单独替换 .venv 内 torch。
- 字幕替换功能会删除当前时间线旧字幕项，第一次使用建议先复制时间线测试。
