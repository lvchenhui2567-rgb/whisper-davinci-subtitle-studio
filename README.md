# Whisper DaVinci Subtitle Studio

DaVinci Resolve subtitle generation and correction tool integrated with Whisper.

## What is included

- `davinci_whisper_subtitle_studio.py`: main DaVinci subtitle studio script.
- `DaVinci菜单入口/Whisper_Subtitle_Studio.py`: small DaVinci menu bridge using `runpy.run_path(...)`.
- `Install_DaVinci_Whisper_Subtitle_Studio.bat`: creates `.venv` and installs Whisper dependencies.
- `Start_DaVinci_Whisper_Subtitle_Studio.bat`: local launcher for testing.
- `srt_rules.json`: correction rule library.
- `README-使用步骤.txt`: Chinese usage notes.

## What is not included

Large local files are excluded from GitHub:

- `.venv/`
- `models/large-v3-turbo.pt`
- `large_v3_model/`
- caches and generated media

## Model setup

For faster-whisper, place a CTranslate2 model folder here:

```text
large_v3_model/
  config.json
  model.bin
  preprocessor_config.json
  tokenizer.json
  vocabulary.json
```

For openai-whisper, place the `.pt` model here:

```text
models/large-v3-turbo.pt
```

The script prefers `large_v3_model/` first, then falls back to `.pt` model paths.

## DaVinci bridge

Copy this file into DaVinci Resolve's user scripts folder:

```text
DaVinci菜单入口/Whisper_Subtitle_Studio.py
```

Target folder on this workstation:

```text
C:\Users\TSJ-010\AppData\Roaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility
```

Then open it from:

```text
Workspace -> Scripts -> Whisper_Subtitle_Studio
```

## Safety note

The subtitle replacement workflow deletes old subtitle timeline items before inserting the corrected SRT. Test on a duplicated timeline first.
