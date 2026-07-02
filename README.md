# Whisper DaVinci 字幕工作站整合包

使用顺序：

## Step 1：安装 Python

打开文件夹：`1.python安装`

运行：`InstallPython.bat`

如果电脑里已经能识别 `python` 命令，会自动跳过。

## Step 2：安装 Whisper 运行环境

打开文件夹：`2.Whisper安装`

运行：`InstallAll-Step2.bat`

这一步会在下面目录创建独立 `.venv`：

`3.启动和达芬奇集成\WhisperSubtitleStudio\.venv`

不会覆盖 VoxCPM2、IndexTTS 或全局 Python 环境。

## Step 3A：本地启动测试

打开文件夹：`3.启动和达芬奇集成`

运行：`Start_Whisper_Subtitle_Studio.bat`

## Step 3B：安装 DaVinci 菜单入口

打开文件夹：`3.启动和达芬奇集成`

运行：`Install_DaVinci_Menu.bat`

然后重启 DaVinci Resolve，在菜单里打开：

`Workspace > Scripts > Utility > Whisper_Subtitle_Studio`

## 模型位置

faster-whisper 模型：

`3.启动和达芬奇集成\WhisperSubtitleStudio\large_v3_model`

openai-whisper `.pt` 兜底模型：

`3.启动和达芬奇集成\WhisperSubtitleStudio\models\large-v3-turbo.pt`

主脚本会优先使用 `large_v3_model`，因此本地整合包默认走 faster-whisper。

## GitHub 备份说明

GitHub 仓库只备份脚本、安装器、桥接入口、规则库和说明。

这些大文件不会上传：

- `.venv/`
- `large_v3_model/`
- `models/`
- 缓存和输出文件

## 注意事项

- 不要改变整合包内部目录结构。
- 目标电脑如果有 NVIDIA 显卡，建议先安装或更新 NVIDIA 驱动。
- 当前安装脚本默认安装 pip 官方依赖；如需 CUDA 加速版 PyTorch，可后续单独替换 `.venv` 内 torch。
- 字幕替换功能会删除当前时间线旧字幕项，第一次使用建议先复制时间线测试。
