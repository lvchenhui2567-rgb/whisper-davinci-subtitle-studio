import sys
import os
import json
import importlib.util
from pathlib import Path
from types import SimpleNamespace

APP_ROOT = Path(__file__).resolve().parent
VENV_SITE_PACKAGES = APP_ROOT / ".venv" / "Lib" / "site-packages"
WHISPER_MODEL_CANDIDATES = [
    APP_ROOT / "large_v3_model",
    APP_ROOT / "models" / "large-v3-turbo.pt",
    Path(r"D:\WhisperWebUI整合包\2.whisper+ffmpeg安装\models\large-v3-turbo.pt"),
    Path.home() / ".cache" / "whisper" / "large-v3-turbo.pt",
]

if VENV_SITE_PACKAGES.exists():
    sys.path.insert(0, str(VENV_SITE_PACKAGES))


def load_resolve_module():
    try:
        import DaVinciResolveScript as bmd
        return bmd
    except ImportError:
        module_path = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Developer" / "Scripting" / "Modules" / "DaVinciResolveScript.py"
        if not module_path.exists():
            return None
        spec = importlib.util.spec_from_file_location("DaVinciResolveScript", str(module_path))
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules["DaVinciResolveScript"] = module
        spec.loader.exec_module(module)
        return module


def get_whisper_model_source():
    for candidate in WHISPER_MODEL_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return "large-v3"


class OpenAIWhisperAdapter:
    def __init__(self, model_source):
        import whisper

        self.model = whisper.load_model(model_source)

    def transcribe(self, audio_path, **kwargs):
        result = self.model.transcribe(
            audio_path,
            language=kwargs.get("language", "zh"),
            initial_prompt=kwargs.get("initial_prompt"),
            condition_on_previous_text=kwargs.get("condition_on_previous_text", False),
            word_timestamps=kwargs.get("word_timestamps", True),
            verbose=False,
        )
        segments = []
        for segment in result.get("segments", []):
            words = []
            for word in segment.get("words") or []:
                words.append(SimpleNamespace(
                    word=word.get("word", ""),
                    start=float(word.get("start", segment.get("start", 0.0))),
                    end=float(word.get("end", segment.get("end", 0.0))),
                ))
            segments.append(SimpleNamespace(
                start=float(segment.get("start", 0.0)),
                end=float(segment.get("end", 0.0)),
                text=segment.get("text", ""),
                words=words,
            ))
        return segments, None


def load_whisper_model_for_studio(model_source, status_callback=None):
    source_path = Path(model_source)
    if source_path.suffix.lower() == ".pt":
        if status_callback:
            status_callback("⏳ [2/3] 检测到 openai-whisper .pt 模型，正在加载兼容模式...")
        return OpenAIWhisperAdapter(str(source_path))

    try:
        from faster_whisper import WhisperModel

        if status_callback:
            status_callback("⏳ [2/3] 正在加载 faster-whisper 模型...")
        if os.path.exists(model_source):
            return WhisperModel(model_source, device="cuda", compute_type="float16", local_files_only=True)
        return WhisperModel(model_source, device="cuda", compute_type="float16")
    except Exception as faster_error:
        try:
            if status_callback:
                status_callback("⏳ [2/3] faster-whisper 不可用，正在切换 openai-whisper...")
            return OpenAIWhisperAdapter(model_source)
        except Exception as openai_error:
            raise RuntimeError(f"Whisper 加载失败。faster-whisper: {faster_error}; openai-whisper: {openai_error}")

# ================= 1. 达芬奇黑洞防崩溃补丁 =================
class DevNull:
    def write(self, *args, **kwargs): pass
    def flush(self, *args, **kwargs): pass
    def isatty(self): return False
    @property
    def encoding(self): return 'utf-8'
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

sys.stdout = DevNull()
sys.stderr = DevNull()
# ===========================================================

dvr_script = load_resolve_module()
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import difflib
import re
import inspect

class DaVinciSubtitleStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("达芬奇 AI 字幕终极工作站 (含媒体池联动 + 记忆词库)")
        self.root.geometry("1050x780")
        self.root.attributes('-topmost', True)
        self.root.configure(bg="#1A1A1C")
        
        # --- 全局变量 ---
        self.audio_path = ""
        self.current_srt_path = "" 
        self.srt_dict = {}  # 媒体池下拉菜单字典
        self.rules = []
        self.last_search_pos = "1.0"
        self.last_search_word = ""
        
        # --- 词库持久化路径 ---
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.rules_file = os.path.join(script_dir, "srt_rules.json")
        
        # --- 初始化达芬奇 API：没有打开项目时也允许先使用本地 SRT 校对功能 ---
        try:
            self.resolve = dvr_script.scriptapp("Resolve") if dvr_script else None
            self.project_manager = self.resolve.GetProjectManager() if self.resolve else None
            self.project = self.project_manager.GetCurrentProject() if self.project_manager else None
            self.media_pool = self.project.GetMediaPool() if self.project else None
        except Exception:
            self.resolve, self.project_manager, self.project, self.media_pool = None, None, None, None
        
        # --- UI 样式配置 ---
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TNotebook", background="#1A1A1C", borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#2D2D30", foreground="#E0E0E0", padding=[15, 5], font=("Microsoft YaHei", 10, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", "#5294E2")], foreground=[("selected", "white")])
        self.style.configure("Horizontal.TProgressbar", foreground='#5294E2', background='#5294E2')

        # --- 构建选项卡 ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tab_gen = tk.Frame(self.notebook, bg="#1A1A1C")
        self.tab_edit = tk.Frame(self.notebook, bg="#1A1A1C")
        
        self.notebook.add(self.tab_gen, text="🎙️ 步骤一: AI 极速生成台")
        self.notebook.add(self.tab_edit, text="✍️ 步骤二: 时间线直抓校对台")
        
        # --- 构建子界面 ---
        self.setup_gen_ui()
        self.setup_edit_ui()
        
        # --- 初始化加载数据 ---
        self.load_rules()
        self.refresh_dropdown()

    # ==========================
    #      TAB 1: AI 生成台
    # ==========================
    def setup_gen_ui(self):
        bg_color = "#1A1A1C"
        card_color = "#2D2D30"
        fg_color = "#E0E0E0"
        accent_color = "#5294E2"
        
        top_frame = tk.Frame(self.tab_gen, bg=bg_color, pady=15)
        top_frame.pack(fill=tk.X, padx=15)
        
        tk.Label(top_frame, text="1. 载入音频 (建议在达芬奇先原位渲染干净人声):", bg=bg_color, fg=fg_color, font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.audio_var = tk.StringVar(value="等待选择音频...")
        tk.Entry(top_frame, textvariable=self.audio_var, state='readonly', bg=card_color, fg="#A0A0A0", borderwidth=0).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 10))
        tk.Button(top_frame, text="📂 浏览音频", bg=accent_color, fg="white", borderwidth=0, padx=15, command=self.select_audio).pack(side=tk.RIGHT)
        
        mid_frame = tk.Frame(self.tab_gen, bg=bg_color)
        mid_frame.pack(fill=tk.BOTH, expand=True, padx=15)
        
        tk.Label(mid_frame, text="2. 粘贴文稿 (纯听写模式无需填写):", bg=bg_color, fg=fg_color, font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        # 【优化】：加入 height=10 限制高度，防止挤走下方的按钮
        self.text_input = tk.Text(mid_frame, wrap=tk.WORD, height=10, bg=card_color, fg="#CCCCCC", font=("Consolas", 11), borderwidth=0, padx=10, pady=10, insertbackground="white")
        self.text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = tk.Scrollbar(mid_frame, command=self.text_input.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_input.config(yscrollcommand=scroll.set)

        bot_frame = tk.Frame(self.tab_gen, bg=bg_color, pady=15)
        bot_frame.pack(fill=tk.X, padx=15)
        
        self.fps_fix_var = tk.BooleanVar(value=True)
        tk.Checkbutton(bot_frame, text="开启 59.94 帧率时间轴补偿 (防字幕越跑越快)", 
                       variable=self.fps_fix_var, bg=bg_color, fg="#D48B2A", 
                       selectcolor=card_color, font=("Microsoft YaHei", 9, "bold")).pack(anchor="w", pady=(0, 10))
        
        self.status_var = tk.StringVar(value="Ready. 系统已就绪。等待音频接入。")
        tk.Label(bot_frame, textvariable=self.status_var, bg=bg_color, fg="#4CAF50").pack(pady=(0, 5))
        self.progress = ttk.Progressbar(bot_frame, mode='indeterminate')
        
        btn_frame = tk.Frame(bot_frame, bg=bg_color)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self.run_pure_btn = tk.Button(btn_frame, text="🎙️ 一键盲听生成 (精细防丢字)", 
                                 bg="#2E7D32", fg="white", borderwidth=0, font=("Microsoft YaHei", 11, "bold"),
                                 pady=10, command=lambda: self.start_worker(pure_asr=True))
        self.run_pure_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.run_align_btn = tk.Button(btn_frame, text="🚀 启动严格对齐 (依据文稿)", 
                                 bg="#D48B2A", fg="white", borderwidth=0, font=("Microsoft YaHei", 11, "bold"),
                                 pady=10, command=lambda: self.start_worker(pure_asr=False))
        self.run_align_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))

    # ==========================
    #      TAB 2: 校对修改台
    # ==========================
    def setup_edit_ui(self):
        bg_color = "#1A1A1C"
        card_color = "#2D2D30"
        fg_color = "#E0E0E0"
        btn_bg = "#3A3A42"
        
        # 【优化】：重构顶栏，恢复媒体池下拉选择
        top_frame = tk.Frame(self.tab_edit, bg=bg_color, pady=10)
        top_frame.pack(fill=tk.X, padx=10)
        
        tk.Button(top_frame, text="⬇️ 抓取时间线", bg="#4CAF50", fg="white", font=("Microsoft YaHei", 10, "bold"), 
                  borderwidth=0, padx=10, command=lambda: self.fetch_timeline_subtitles(auto=False)).pack(side=tk.LEFT)
                  
        tk.Label(top_frame, text=" 或选媒体池:", bg=bg_color, fg=fg_color).pack(side=tk.LEFT, padx=(10, 2))
        
        self.combo_var = tk.StringVar()
        self.srt_combo = ttk.Combobox(top_frame, textvariable=self.combo_var, state='readonly', width=30)
        self.srt_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.srt_combo.bind("<<ComboboxSelected>>", self.on_combo_select)
        
        tk.Button(top_frame, text="🔄 刷新", bg=btn_bg, fg=fg_color, borderwidth=0, padx=8, command=self.refresh_dropdown).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(top_frame, text="📂 浏览本地", bg="#5294E2", fg="white", borderwidth=0, padx=10, command=self.manual_select).pack(side=tk.RIGHT)

        main_frame = tk.Frame(self.tab_edit, bg=bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        left_frame = tk.Frame(main_frame, bg=bg_color, width=500)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False) 
        
        tk.Label(left_frame, text="📄 SRT 文本内容 (可预览、可手动编辑修改)", bg=bg_color, fg=fg_color).pack(anchor="w", pady=(0,5))
        
        scroll = tk.Scrollbar(left_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_preview = tk.Text(left_frame, wrap=tk.WORD, yscrollcommand=scroll.set, bg=card_color, fg="#CCCCCC", font=("Consolas", 11), insertbackground="white", borderwidth=0, padx=10, pady=10)
        self.text_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.text_preview.yview)
        
        self.text_preview.tag_config("highlight", background="#D48B2A", foreground="white")

        right_frame = tk.Frame(main_frame, bg=bg_color)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(15, 0))

        tk.Label(right_frame, text="🔍 记忆词库与全局替换", bg=bg_color, fg=fg_color, font=("Microsoft YaHei", 11, "bold")).pack(anchor="w", pady=(0, 10))
        
        tk.Button(right_frame, text="⚡ 一键应用整个词库 (批量修正本文)", bg="#2E7D32", fg="white", font=("Microsoft YaHei", 10, "bold"), borderwidth=0, command=self.apply_all_rules).pack(fill=tk.X, pady=(0, 10), ipady=6)

        input_frame = tk.Frame(right_frame, bg=bg_color)
        input_frame.pack(fill=tk.X)
        
        tk.Label(input_frame, text="查找错字:", bg=bg_color, fg=fg_color).grid(row=0, column=0, sticky="w")
        find_container = tk.Frame(input_frame, bg=bg_color)
        find_container.grid(row=0, column=1, pady=5, padx=(5,0), sticky="w")
        self.find_entry = tk.Entry(find_container, width=15, bg=card_color, fg="white", borderwidth=0)
        self.find_entry.pack(side=tk.LEFT, ipady=4)
        tk.Button(find_container, text="🔽 定位", bg="#4CAF50", fg="white", borderwidth=0, command=self.find_next_text, cursor="hand2").pack(side=tk.LEFT, padx=(5,0), ipady=2, ipadx=5)
        
        tk.Label(input_frame, text="替换为:", bg=bg_color, fg=fg_color).grid(row=1, column=0, sticky="w")
        self.replace_entry = tk.Entry(input_frame, width=22, bg=card_color, fg="white", borderwidth=0)
        self.replace_entry.grid(row=1, column=1, pady=5, padx=(5,0), ipady=4)
        
        tk.Button(right_frame, text="➕ 替换当前并永久加入词库", bg=btn_bg, fg="white", borderwidth=0, command=self.add_and_preview_rule).pack(fill=tk.X, pady=10, ipady=5)
        
        rule_header = tk.Frame(right_frame, bg=bg_color)
        rule_header.pack(fill=tk.X)
        tk.Label(rule_header, text="📖 本地常驻词库：", bg=bg_color, fg=fg_color).pack(side=tk.LEFT)
        tk.Button(rule_header, text="📥 导入", bg="#5294E2", fg="white", borderwidth=0, command=self.import_json_rules).pack(side=tk.RIGHT, padx=(5, 0))
        tk.Button(rule_header, text="📤 导出", bg=btn_bg, fg=fg_color, borderwidth=0, command=self.export_json_rules).pack(side=tk.RIGHT)
        self.rule_listbox = tk.Listbox(right_frame, height=7, bg=card_color, fg="#CCCCCC", borderwidth=0)
        self.rule_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        tk.Button(right_frame, text="➖ 从词库中彻底删除选中规则", bg=btn_bg, fg=fg_color, borderwidth=0, command=self.delete_rule).pack(fill=tk.X, ipady=3)
        
        tk.Button(right_frame, text="📝 导出当前字幕为 TXT 文稿", bg="#455A64", fg="white", font=("Microsoft YaHei", 10, "bold"), borderwidth=0, command=self.export_current_subtitles_to_txt).pack(fill=tk.X, pady=(14, 0), ipady=7)
        tk.Button(right_frame, text="💾 终版保存并自动导入媒体池", bg="#D48B2A", fg="white", font=("Microsoft YaHei", 12, "bold"), borderwidth=0, command=self.execute_and_import).pack(fill=tk.X, pady=(20, 0), ipady=12)

    # ==========================
    #      持久化词库读写逻辑
    # ==========================
    def load_rules(self):
        if os.path.exists(self.rules_file):
            try:
                self._load_json_data(self.rules_file, silent=True)
            except Exception as e:
                print(f"读取词库失败: {e}")

    def _load_json_data(self, path, silent=False):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            add_count = 0
            for pair in data:
                if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                    continue
                f_text = str(pair[0]).strip()
                r_text = str(pair[1]).strip()
                if not f_text:
                    continue
                if not any(rule[0] == f_text and rule[1] == r_text for rule in self.rules):
                    self.rules.append([f_text, r_text])
                    self.rule_listbox.insert(tk.END, f" {f_text}  -->  {r_text}")
                    add_count += 1

            if not silent:
                messagebox.showinfo("导入成功", f"已导入 {add_count} 条新规则。")
        except Exception as e:
            if not silent:
                messagebox.showerror("导入失败", f"规则文件解析失败：\n{e}")

    def import_json_rules(self):
        path = filedialog.askopenfilename(title="选择规则 JSON", filetypes=[("JSON Files", "*.json")])
        if not path:
            return
        self._load_json_data(path, silent=False)
        self.save_rules()

    def export_json_rules(self):
        if not self.rules:
            messagebox.showwarning("提示", "当前没有规则可导出。")
            return
        save_path = filedialog.asksaveasfilename(
            title="导出规则库",
            defaultextension=".json",
            initialfile="srt_rules.json",
            filetypes=[("JSON Files", "*.json")]
        )
        if not save_path:
            return
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("导出成功", f"规则库已保存到：\n{save_path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"无法保存规则库：\n{e}")

    def save_rules(self):
        try:
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("词库保存失败", f"无法写入本地词库文件：\n{e}")

    def apply_all_rules(self):
        if not self.rules:
            messagebox.showinfo("提示", "当前本地词库为空，请先添加规则。")
            return
            
        current_content = self.text_preview.get(1.0, tk.END)
        if not current_content.strip():
            messagebox.showwarning("提示", "当前没有需要修改的字幕内容！")
            return
            
        new_content = current_content
        replace_count = 0
        for f_text, r_text in self.rules:
            if f_text in new_content:
                replace_count += new_content.count(f_text)
                new_content = new_content.replace(f_text, r_text)
                
        if replace_count > 0:
            self.text_preview.delete(1.0, tk.END)
            self.text_preview.insert(tk.END, new_content.strip())
            self.last_search_pos = "1.0"
            self.last_search_word = ""
            messagebox.showinfo("洗稿完成", f"一键套用词库成功，共计纠正 {replace_count} 处。")
        else:
            messagebox.showinfo("完美", "通读全文，未发现词库中的错别字！")

    def add_and_preview_rule(self):
        f_text = self.find_entry.get().strip()
        r_text = self.replace_entry.get().strip()
        if f_text:
            if any(rule[0] == f_text for rule in self.rules):
                messagebox.showwarning("提示", f"词库中已存在关于【{f_text}】的规则，请勿重复添加。")
                return

            current_content = self.text_preview.get(1.0, tk.END)
            replace_count = current_content.count(f_text)

            self.rules.append([f_text, r_text])
            self.rule_listbox.insert(tk.END, f" {f_text}  -->  {r_text}")
            self.save_rules()

            if f_text in current_content:
                new_content = current_content.replace(f_text, r_text)
                self.text_preview.delete(1.0, tk.END)
                self.text_preview.insert(tk.END, new_content.strip())
            
            self.find_entry.delete(0, tk.END)
            self.replace_entry.delete(0, tk.END)
            self.text_preview.tag_remove("highlight", "1.0", tk.END)
            self.last_search_pos = "1.0"
            self.last_search_word = ""
            messagebox.showinfo("规则已添加", f"已加入词库，并替换当前字幕中的 {replace_count} 处。")

    def delete_rule(self):
        selected = self.rule_listbox.curselection()
        if selected:
            idx = selected[0]
            self.rule_listbox.delete(idx)
            self.rules.pop(idx)
            self.save_rules() 

    # ==========================
    #      功能: AI 生成逻辑
    # ==========================
    def select_audio(self):
        path = filedialog.askopenfilename(title="选择音频", filetypes=[("音频文件", "*.wav *.mp3 *.m4a *.aac")])
        if path:
            self.audio_path = path
            self.audio_var.set(os.path.basename(path))

    def format_srt_time(self, seconds, multiplier=1.0):
        adjusted_seconds = seconds * multiplier
        hrs = int(adjusted_seconds // 3600)
        mins = int((adjusted_seconds % 3600) // 60)
        secs = int(adjusted_seconds % 60)
        msecs = int(round((adjusted_seconds - int(adjusted_seconds)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"

    def update_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    def start_worker(self, pure_asr):
        if not self.audio_path or not os.path.exists(self.audio_path):
            messagebox.showerror("错误", "请先选择有效的音频文件！")
            return
        
        raw_script = self.text_input.get("1.0", tk.END).strip()
        if not pure_asr and not raw_script:
            messagebox.showwarning("提示", "严格对齐模式需要输入口播文稿！或者请使用盲听模式。")
            return

        self.run_pure_btn.config(state=tk.DISABLED)
        self.run_align_btn.config(state=tk.DISABLED)
        self.progress.pack(fill=tk.X, pady=(0, 10))
        self.progress.start(15)
        self.update_status("⏳ [1/3] 正在申请显存并分配 CUDA 核心...")
        
        threading.Thread(target=self.process_ai, args=(raw_script, pure_asr), daemon=True).start()

    def process_ai(self, raw_script, pure_asr):
        try:
            model_source = get_whisper_model_source()
            if os.path.exists(model_source):
                self.update_status(f"⏳ [2/3] 正在加载本地 Whisper 模型：{os.path.basename(model_source)}")
            else:
                self.update_status("⏳ [2/3] 未找到本地模型，正在加载系统缓存 Large-v3 模型...")
            model = load_whisper_model_for_studio(model_source, self.update_status)
            
            time_multiplier = 1.001 if self.fps_fix_var.get() else 1.0 
            srt_output = ""

            if pure_asr:
                self.update_status("🔥 [3/3] 引擎全开！正在执行精细盲听 (字级时间轴+高敏VAD)...")
                natural_prompt = "大家好，欢迎收看这期关于达芬奇Resolve和Fusion的高阶教程。今天Han Lu和Li Jieling会重点讲到Python与Ollama的自动化应用。"
                
                segments, _ = model.transcribe(
                    self.audio_path, language="zh", initial_prompt=natural_prompt,
                    beam_size=5, word_timestamps=True, condition_on_previous_text=False, 
                    vad_filter=True, vad_parameters=dict(min_silence_duration_ms=450, threshold=0.35, speech_pad_ms=200) 
                )
                
                line_count = 1
                MAX_CHARS_PER_LINE = 20 
                for s in segments:
                    current_line = ""
                    start_t = None
                    for w in s.words:
                        word_text = w.word.strip()
                        if not word_text: continue
                        if start_t is None: start_t = w.start
                        current_line += word_text
                        
                        if len(current_line) >= MAX_CHARS_PER_LINE or any(p in word_text for p in ['。', '？', '！']):
                            clean_line = current_line.strip('，。？！、 ') 
                            if clean_line:
                                srt_output += f"{line_count}\n{self.format_srt_time(start_t, time_multiplier)} --> {self.format_srt_time(w.end, time_multiplier)}\n{clean_line}\n\n"
                                line_count += 1
                            current_line = ""
                            start_t = None 
                    
                    clean_residual = current_line.strip('，。？！、 ')
                    if clean_residual and start_t is not None:
                        srt_output += f"{line_count}\n{self.format_srt_time(start_t, time_multiplier)} --> {self.format_srt_time(s.end, time_multiplier)}\n{clean_residual}\n\n"
                        line_count += 1
                        
            else:
                self.update_status("🔥 [3/3] 引擎全开！正在执行 VAD 过滤与序列比对...")
                segments, _ = model.transcribe(
                    self.audio_path, initial_prompt=raw_script.replace('\n', '。'), language="zh",
                    beam_size=5, word_timestamps=True, condition_on_previous_text=False, 
                    vad_filter=True, vad_parameters=dict(min_silence_duration_ms=450, threshold=0.35, speech_pad_ms=200) 
                )
                
                w_data = []
                for s in segments:
                    for w in s.words:
                        clean_word = "".join(filter(str.isalnum, w.word))
                        if not clean_word: continue
                        dur = (w.end - w.start) / len(clean_word)
                        for j, ch in enumerate(clean_word): w_data.append({'char': ch, 't': w.start + dur * j})
                
                u_data = []
                user_lines = [l.strip() for l in raw_script.split('\n') if l.strip()]
                for l_idx, line in enumerate(user_lines):
                    clean_line = "".join(filter(str.isalnum, line))
                    for ch in clean_line: u_data.append({'char': ch, 'line_idx': l_idx, 't': None})
                
                w_chars = [x['char'] for x in w_data]
                u_chars = [x['char'] for x in u_data]
                matcher = difflib.SequenceMatcher(None, w_chars, u_chars)
                
                for match in matcher.get_matching_blocks():
                    w_i, u_i, size = match
                    for k in range(size): u_data[u_i + k]['t'] = w_data[w_i + k]['t']
                        
                last_t = 0.0
                for u in u_data:
                    if u['t'] is not None: last_t = u['t']
                    else: u['t'] = last_t
                
                last_end = 0.0
                for i, line in enumerate(user_lines):
                    times = [u['t'] for u in u_data if u['line_idx'] == i and u['t'] is not None]
                    if times:
                        start_t = min(times)
                        end_t = max(times) + 0.3 
                    else:
                        start_t = last_end
                        end_t = start_t + 1.0 
                    
                    last_end = end_t
                    srt_output += f"{i+1}\n{self.format_srt_time(start_t, time_multiplier)} --> {self.format_srt_time(end_t, time_multiplier)}\n{line}\n\n"
            
            mode_tag = "AI初稿版"
            base = os.path.splitext(self.audio_path)[0]
            srt_path = f"{base}_{mode_tag}.srt"
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_output.strip())
            
            friendly_path = srt_path.replace("\\", "/")
            self.media_pool.ImportMedia([friendly_path])
            
            self.root.after(0, lambda: self.finish_gen_and_handoff(srt_path))
            
        except Exception as e:
            self.root.after(0, lambda: self.error_ui(str(e)))

    def finish_gen_and_handoff(self, path):
        self.progress.stop()
        self.progress.pack_forget()
        self.run_pure_btn.config(state=tk.NORMAL)
        self.run_align_btn.config(state=tk.NORMAL)
        self.status_var.set("✨ 生成完成！已自动导入媒体池，并加载至校对台。")
        
        self.current_srt_path = path
        
        # 【新增】：将刚生成的记录加入下拉菜单并自动选中
        filename = os.path.basename(path)
        self.srt_dict[filename] = path
        options = list(self.srt_combo['values'])
        if filename not in options:
            options.append(filename)
            self.srt_combo['values'] = options
        self.combo_var.set(filename)
        
        self.load_file_to_preview(path)
        self.notebook.select(self.tab_edit)
        
        if self.rules:
            messagebox.showinfo("生成完毕", "字幕已生成！\n\n提示：您可以直接点击右侧绿色的【⚡ 一键应用整个词库】按钮，系统会自动过滤常发错别字。")

    def error_ui(self, err):
        self.progress.stop()
        self.progress.pack_forget()
        self.run_pure_btn.config(state=tk.NORMAL)
        self.run_align_btn.config(state=tk.NORMAL)
        self.status_var.set("❌ 发生错误")
        messagebox.showerror("运算失败", f"系统报错，请检查环境：\n\n{err}")

    # ==========================
    #      功能: 媒体池下拉菜单逻辑
    # ==========================
    def _scan_all_srts(self, folder):
        if not folder: return
        clips = folder.GetClipList()
        for clip in clips:
            path = clip.GetClipProperty("File Path")
            if path and str(path).lower().endswith('.srt'):
                filename = os.path.basename(str(path))
                if filename in self.srt_dict and self.srt_dict[filename] != str(path):
                    filename = f"{filename} ({clip.GetName()})"
                self.srt_dict[filename] = str(path)

        for sub in folder.GetSubFolderList():
            self._scan_all_srts(sub)

    def refresh_dropdown(self):
        self.srt_dict.clear()
        try:
            if not self.media_pool:
                self.srt_combo['values'] = []
                self.combo_var.set("未连接达芬奇项目，可浏览本地 SRT")
                return
            root_folder = self.media_pool.GetRootFolder()
            self._scan_all_srts(root_folder)
            
            if self.srt_dict:
                options = list(self.srt_dict.keys())
                self.srt_combo['values'] = options
                # 不强制重置用户的当前选择，除非当前内容为空
                if not self.combo_var.get() or self.combo_var.get() not in options:
                    self.srt_combo.current(0) 
                    self.on_combo_select(None) 
            else:
                self.srt_combo['values'] = []
                self.combo_var.set("未找到 SRT...")
                self.text_preview.delete(1.0, tk.END)
                self.current_srt_path = ""
        except Exception:
            self.combo_var.set("扫描达芬奇项目失败...")

    def on_combo_select(self, event):
        selected_name = self.combo_var.get()
        if selected_name in self.srt_dict:
            self.current_srt_path = self.srt_dict[selected_name]
            self.load_file_to_preview(self.current_srt_path)

    # ==========================
    #      功能: 时间线抓取与校对
    # ==========================
    def frame_to_srt_timecode(self, frame, fps, start_frame):
        relative_frame = frame - start_frame
        if relative_frame < 0: relative_frame = 0
        total_seconds = relative_frame / fps
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int(round((total_seconds - int(total_seconds)) * 1000))
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def fetch_timeline_subtitles(self, auto=False):
        if not self.project:
            if not auto: messagebox.showerror("错误", "请先在达芬奇中打开一个项目，或使用【浏览本地】选择 SRT。")
            return
        timeline = self.project.GetCurrentTimeline()
        if not timeline:
            if not auto: messagebox.showerror("错误", "未找到活动时间线！")
            return
            
        track_count = timeline.GetTrackCount("subtitle")
        if track_count == 0:
            if not auto: messagebox.showinfo("提示", "当前时间线上没有字幕轨道！")
            return
            
        items = timeline.GetItemListInTrack("subtitle", 1)
        if not items:
            if not auto: messagebox.showinfo("提示", "第一层字幕轨道是空的！")
            return
            
        try:
            fps = float(timeline.GetSetting("timelineFrameRate"))
            start_frame = timeline.GetStartFrame()
            
            srt_content = ""
            for i, item in enumerate(items):
                text = item.GetName()
                if text.startswith("Subtitle") or not text:
                    prop_text = item.GetProperty("Text")
                    if prop_text: text = prop_text
                    
                start_tc = self.frame_to_srt_timecode(item.GetStart(), fps, start_frame)
                end_tc = self.frame_to_srt_timecode(item.GetEnd(), fps, start_frame)
                
                srt_content += f"{i+1}\n{start_tc} --> {end_tc}\n{text}\n\n"
                
            self.text_preview.delete(1.0, tk.END)
            self.text_preview.insert(tk.END, srt_content.strip())
            
            self.current_srt_path = "" 
            self.combo_var.set("<- 当前为抓取自时间线的未保存内容")
            self.last_search_pos = "1.0"
            self.last_search_word = ""
            
            if not auto: messagebox.showinfo("成功", f"成功抓取 {len(items)} 条字幕！\n\n如果本地词库已有规则，可以直接点击【⚡ 一键应用整个词库】。")
            
        except Exception as e:
            messagebox.showerror("抓取失败", f"发生了意外错误: {str(e)}")

    def manual_select(self):
        path = filedialog.askopenfilename(title="选择 SRT 文件", filetypes=[("SRT Files", "*.srt")])
        if path:
            self.current_srt_path = path
            filename = os.path.basename(path)
            self.srt_dict[filename] = path
            options = list(self.srt_combo['values'])
            if filename not in options:
                options.append(filename)
                self.srt_combo['values'] = options
            self.combo_var.set(filename)
            self.load_file_to_preview(path)

    def load_file_to_preview(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_preview.delete(1.0, tk.END)
            self.text_preview.insert(tk.END, content)
            self.last_search_pos = "1.0"
            self.last_search_word = ""
        except Exception as e:
            self.text_preview.delete(1.0, tk.END)
            self.text_preview.insert(tk.END, f"无法读取文件内容：\n{e}")

    def find_next_text(self):
        target = self.find_entry.get()
        if not target: return
        if target != self.last_search_word:
            self.last_search_pos = "1.0"
            self.last_search_word = target
        self.text_preview.tag_remove("highlight", "1.0", tk.END)
        pos = self.text_preview.search(target, self.last_search_pos, stopindex=tk.END)
        if not pos:
            pos = self.text_preview.search(target, "1.0", stopindex=tk.END)
            if not pos:
                messagebox.showinfo("提示", f"文本中未找到内容：'{target}'")
                return
        end_pos = f"{pos}+{len(target)}c"
        self.text_preview.tag_add("highlight", pos, end_pos)
        self.text_preview.mark_set(tk.INSERT, pos)
        self.text_preview.see(pos)
        start_time = self._find_block_start_time_for_text_index(pos)
        if start_time:
            self.jump_playhead_to_srt_time(start_time)
        self.last_search_pos = end_pos

    def srt_content_to_plain_text(self, content):
        lines = []
        for raw_block in re.split(r'\n\s*\n', content.strip()):
            block_lines = [line.strip() for line in raw_block.splitlines() if line.strip()]
            if not block_lines:
                continue

            text_lines = []
            for line in block_lines:
                if re.fullmatch(r'\d+', line):
                    continue
                if '-->' in line:
                    continue
                text_lines.append(line)

            if text_lines:
                lines.append(''.join(text_lines))
        return '\n'.join(lines).strip()

    def export_current_subtitles_to_txt(self):
        content = self.text_preview.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("提示", "当前没有字幕内容可以导出。")
            return

        plain_text = self.srt_content_to_plain_text(content)
        if not plain_text:
            messagebox.showwarning("提示", "未能从当前内容中解析出字幕正文。")
            return

        if self.current_srt_path and os.path.exists(self.current_srt_path):
            initial_dir = os.path.dirname(os.path.abspath(self.current_srt_path))
            initial_name = os.path.splitext(os.path.basename(self.current_srt_path))[0] + "_文稿.txt"
        else:
            initial_dir = os.path.expanduser("~")
            try:
                timeline = self.project.GetCurrentTimeline() if self.project else None
                timeline_name = timeline.GetName() if timeline else "当前字幕"
            except Exception:
                timeline_name = "当前字幕"
            initial_name = f"{timeline_name}_文稿.txt"

        save_path = filedialog.asksaveasfilename(
            title="导出 TXT 文稿",
            defaultextension=".txt",
            initialdir=initial_dir,
            initialfile=initial_name,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not save_path:
            return

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(plain_text + "\n")
            messagebox.showinfo("导出完成", f"TXT 文稿已保存：\n{save_path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"无法保存 TXT 文件：\n{e}")

    def _find_block_start_time_for_text_index(self, text_index):
        content = self.text_preview.get("1.0", "end-1c")
        try:
            hit_offset = self.text_preview.count("1.0", text_index, "chars")[0]
        except Exception:
            return None

        pattern = re.compile(
            r'(?ms)(?:^|\n)\s*\d+\s*\n'
            r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*'
            r'\d{2}:\d{2}:\d{2},\d{3}.*?(?=\n\s*\n|\Z)'
        )
        for match in pattern.finditer(content):
            if match.start() <= hit_offset <= match.end():
                return match.group(1)
        return None

    def srt_time_to_frames(self, time_str, fps):
        h, m, s_ms = time_str.split(':')
        s, ms = s_ms.split(',')
        total_ms = (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)
        return int(round(total_ms * fps / 1000.0))

    def frames_to_resolve_timecode(self, frames, fps):
        nominal_fps = int(round(fps))
        if abs(fps - 29.97) < 0.02 or abs(fps - 59.94) < 0.02:
            return self.frames_to_drop_frame_timecode(frames, nominal_fps)
        total_seconds, frame_part = divmod(int(round(frames)), nominal_fps)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}:{frame_part:02d}"

    def frames_to_drop_frame_timecode(self, frames, nominal_fps):
        frames = int(round(frames))
        drop_frames = 2 if nominal_fps == 30 else 4
        frames_per_hour = nominal_fps * 60 * 60
        frames_per_24_hours = frames_per_hour * 24
        frames_per_10_minutes = nominal_fps * 60 * 10 - drop_frames * 9
        frames_per_minute = nominal_fps * 60 - drop_frames

        frames = frames % frames_per_24_hours
        ten_minute_chunks = frames // frames_per_10_minutes
        remaining_frames = frames % frames_per_10_minutes
        timecode_frames = frames + drop_frames * 9 * ten_minute_chunks
        if remaining_frames >= drop_frames:
            timecode_frames += drop_frames * ((remaining_frames - drop_frames) // frames_per_minute)

        h = timecode_frames // frames_per_hour
        m = (timecode_frames % frames_per_hour) // (nominal_fps * 60)
        s = (timecode_frames % (nominal_fps * 60)) // nominal_fps
        f = timecode_frames % nominal_fps
        return f"{h:02d}:{m:02d}:{s:02d};{f:02d}"

    def frames_to_offset_timecode(self, frames, fps):
        frames = max(0, int(round(frames)))
        nominal_fps = int(round(fps)) or 25
        total_seconds, frame_part = divmod(frames, nominal_fps)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}:{frame_part:02d}"

    def jump_playhead_to_srt_time(self, time_str):
        if not self.project:
            return
        timeline = self.project.GetCurrentTimeline()
        if not timeline:
            return
        try:
            fps = float(timeline.GetSetting("timelineFrameRate") or self.project.GetSetting("timelineFrameRate") or 25.0)
            start_frame = int(timeline.GetStartFrame() or 0)
            target_frames = start_frame + self.srt_time_to_frames(time_str, fps)
            timeline.SetCurrentTimecode(self.frames_to_resolve_timecode(target_frames, fps))
        except Exception:
            pass

    def replace_timeline_subtitles_with_srt(self, imported_items):
        """Delete existing subtitle timeline items, then put the fixed SRT at timeline start."""
        if not self.project or not self.media_pool or not imported_items:
            return False, "未连接达芬奇项目或媒体池导入结果为空"

        timeline = self.project.GetCurrentTimeline()
        if not timeline:
            return False, "当前没有打开的时间线"

        try:
            subtitle_track_count = int(timeline.GetTrackCount("subtitle") or 0)
        except Exception:
            subtitle_track_count = 0

        if subtitle_track_count == 0:
            try:
                if hasattr(timeline, "AddTrack") and timeline.AddTrack("subtitle"):
                    subtitle_track_count = int(timeline.GetTrackCount("subtitle") or 1)
                else:
                    return False, "当前时间线没有字幕轨，且无法自动创建字幕轨。"
            except Exception as e:
                return False, f"自动创建字幕轨失败：{e}"

        old_items = []
        old_first_start = None
        for track_index in range(1, subtitle_track_count + 1):
            try:
                items = timeline.GetItemListInTrack("subtitle", track_index) or []
                old_items.extend(items)
                for item in items:
                    try:
                        item_start = int(item.GetStart() or 0)
                        old_first_start = item_start if old_first_start is None else min(old_first_start, item_start)
                    except Exception:
                        pass
            except Exception:
                pass

        if old_first_start is None:
            try:
                old_first_start = int(timeline.GetStartFrame() or 0)
            except Exception:
                old_first_start = 0

        deleted_count = 0
        if old_items:
            try:
                if timeline.DeleteClips(old_items, False):
                    deleted_count = len(old_items)
                else:
                    return False, "删除旧字幕失败，已停止自动替换，避免新旧字幕混在一起。"
            except Exception as e:
                return False, f"删除旧字幕失败，已停止自动替换：{e}"

        target_track = 1
        try:
            timeline_start_frame = int(timeline.GetStartFrame() or 0)
            fps = float(timeline.GetSetting("timelineFrameRate") or self.project.GetSetting("timelineFrameRate") or 25.0)
        except Exception:
            timeline_start_frame = 0
            fps = 25.0

        tolerance = max(2, int(round(fps)))
        media_item = imported_items[0]

        def collect_subtitle_items():
            found = []
            try:
                for track_index in range(1, int(timeline.GetTrackCount("subtitle") or 0) + 1):
                    found.extend(timeline.GetItemListInTrack("subtitle", track_index) or [])
            except Exception:
                pass
            return found

        def try_insert(label, payload, playhead_frame=None):
            if playhead_frame is not None:
                try:
                    timeline.SetCurrentTimecode(self.frames_to_resolve_timecode(playhead_frame, fps))
                except Exception:
                    pass
            try:
                result = self.media_pool.AppendToTimeline(payload)
            except Exception as exc:
                return False, f"{label} 调用失败：{exc}"

            if not result:
                return False, f"{label} 未被 Resolve 接受"

            new_items = collect_subtitle_items()
            if not new_items:
                return False, f"{label} 后未检测到新字幕项"

            try:
                new_first_start = min(int(item.GetStart() or 0) for item in new_items)
            except Exception:
                new_first_start = None

            if new_first_start is not None and abs(new_first_start - old_first_start) <= tolerance:
                return True, f"{label} 成功：已删除旧字幕 {deleted_count} 条，并把修正版 SRT 放回原字幕起点。"

            try:
                timeline.DeleteClips(new_items, False)
            except Exception:
                pass

            old_tc = self.frames_to_resolve_timecode(old_first_start, fps)
            new_tc = self.frames_to_resolve_timecode(new_first_start, fps) if new_first_start is not None else "未知"
            return False, f"{label} 落点错误：{new_tc}，原始位置应为 {old_tc}，已删除本次错位字幕"

        insert_attempts = [
            ("绝对帧 recordFrame", [{"mediaPoolItem": media_item, "trackIndex": target_track, "recordFrame": old_first_start}], None),
            ("相对帧 recordFrame", [{"mediaPoolItem": media_item, "trackIndex": target_track, "recordFrame": max(0, old_first_start - timeline_start_frame)}], None),
            ("播放头定位", [media_item], old_first_start),
        ]

        errors = []
        for label, payload, playhead_frame in insert_attempts:
            ok, msg = try_insert(label, payload, playhead_frame)
            if ok:
                return True, msg
            errors.append(msg)

        return False, "旧字幕已删除 {0} 条，但三种按原始时间插入方式都失败。\n\n{1}\n\n新 SRT 已在媒体池，请手动拖到原字幕起点。".format(deleted_count, "\n".join(errors))

    def execute_and_import(self):
        final_content = self.text_preview.get(1.0, tk.END).strip()
        if not final_content:
            messagebox.showwarning("提示", "文本为空，无法保存！")
            return
            
        try:
            new_path = ""
            if not self.current_srt_path:
                save_path = filedialog.asksaveasfilename(
                    title="保存新的 SRT 文件", 
                    defaultextension=".srt", 
                    filetypes=[("SRT Files", "*.srt")],
                    initialfile="时间轴最终定稿.srt"
                )
                if not save_path: return 
                new_path = save_path
            else:
                abs_current_path = os.path.abspath(self.current_srt_path)
                base_name = os.path.splitext(abs_current_path)[0]
                if base_name.endswith("_AI初稿版"):
                    base_name = base_name.replace("_AI初稿版", "")
                new_path = f"{base_name}_已精修.srt"
            
            with open(new_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
                
            resolve_friendly_path = new_path.replace("\\", "/")
            imported_items = self.media_pool.ImportMedia([resolve_friendly_path]) if self.media_pool else None
            
            if imported_items:
                timeline_ok, timeline_msg = self.replace_timeline_subtitles_with_srt(imported_items)
                if timeline_ok:
                    messagebox.showinfo("大功告成", f"处理完成！\n\n新文件【{os.path.basename(new_path)}】已自动导入媒体池。\n{timeline_msg}")
                else:
                    messagebox.showwarning("部分成功", f"新文件【{os.path.basename(new_path)}】已自动导入媒体池。\n\n{timeline_msg}")
                self.refresh_dropdown() # 重新扫描一下更新后的媒体池
            else:
                messagebox.showwarning("部分成功", f"文件已生成在：\n{new_path}\n\n但达芬奇拒绝自动导入，请手动拖入媒体池。")
                
        except Exception as e:
            messagebox.showerror("处理失败", f"发生了意外错误:\n\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DaVinciSubtitleStudio(root)
    root.mainloop()
