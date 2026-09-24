"""Giao diện chính của phần mềm - Batch Video Editor."""
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

import templates as tpl_store
from downloader import download_videos
from editor import edit_video, RESOLUTIONS
from subtitle_gen import generate_srt

WORK_DIR = os.path.join(os.path.expanduser("~"), "BatchVideoEditor_temp")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Batch Video Editor")
        self.geometry("880x640")
        self.templates = tpl_store.load_templates()
        self.output_dir = os.path.join(os.path.expanduser("~"), "Desktop", "EditedVideos")
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="both", expand=True)

        # --- Cột trái: nhập link ---
        left = ttk.LabelFrame(top, text="1. Danh sách link video", padding=8)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.url_text = tk.Text(left, height=18, width=45)
        self.url_text.pack(fill="both", expand=True)
        self.url_text.insert("1.0", "# Mỗi link 1 dòng\n")

        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x", pady=6)
        ttk.Button(btn_row, text="Import từ file (.txt/.csv/.xlsx)", command=self.import_links).pack(side="left")
        ttk.Button(btn_row, text="Xóa hết", command=lambda: self.url_text.delete("1.0", "end")).pack(side="left", padx=6)

        # --- Cột phải: tùy chọn ---
        right = ttk.Frame(top)
        right.pack(side="left", fill="both", expand=True)

        opt = ttk.LabelFrame(right, text="2. Tùy chọn edit", padding=8)
        opt.pack(fill="x")

        ttk.Label(opt, text="Mẫu (template):").grid(row=0, column=0, sticky="w", pady=4)
        self.template_var = tk.StringVar(value=list(self.templates.keys())[0] if self.templates else "")
        self.template_combo = ttk.Combobox(opt, textvariable=self.template_var, values=list(self.templates.keys()), state="readonly", width=32)
        self.template_combo.grid(row=0, column=1, sticky="w")
        ttk.Button(opt, text="Quản lý mẫu...", command=self.open_template_manager).grid(row=0, column=2, padx=6)

        ttk.Label(opt, text="Độ phân giải xuất:").grid(row=1, column=0, sticky="w", pady=4)
        self.res_var = tk.StringVar(value="720p (HD)")
        ttk.Combobox(opt, textvariable=self.res_var, values=list(RESOLUTIONS.keys()), state="readonly", width=32).grid(row=1, column=1, sticky="w")

        self.sub_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="Tự động tạo phụ đề (auto subtitle, cần cài faster-whisper)", variable=self.sub_enabled_var).grid(row=2, column=0, columnspan=3, sticky="w", pady=4)

        out_row = ttk.Frame(right, padding=(0, 10))
        out_row.pack(fill="x")
        ttk.Label(out_row, text="Thư mục xuất:").pack(side="left")
        self.out_dir_var = tk.StringVar(value=self.output_dir)
        ttk.Entry(out_row, textvariable=self.out_dir_var, width=40).pack(side="left", padx=6)
        ttk.Button(out_row, text="Chọn...", command=self.pick_output_dir).pack(side="left")

        action_row = ttk.Frame(right)
        action_row.pack(fill="x", pady=8)
        self.start_btn = ttk.Button(action_row, text="▶ Bắt đầu tải + edit hàng loạt", command=self.start_batch)
        self.start_btn.pack(side="left")

        log_frame = ttk.LabelFrame(right, text="Tiến trình", padding=8)
        log_frame.pack(fill="both", expand=True, pady=8)
        self.log_text = tk.Text(log_frame, height=18, state="disabled", bg="#111", fg="#0f0")
        self.log_text.pack(fill="both", expand=True)

    # ---------- Helpers ----------
    def log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.update_idletasks()

    def import_links(self):
        path = filedialog.askopenfilename(filetypes=[("Text/CSV/Excel", "*.txt *.csv *.xlsx")])
        if not path:
            return
        links = []
        if path.lower().endswith(".xlsx"):
            import openpyxl
            wb = openpyxl.load_workbook(path)
            ws = wb.active
            for row in ws.iter_rows(values_only=True):
                for cell in row:
                    if cell and str(cell).startswith("http"):
                        links.append(str(cell).strip())
        else:
            with open(path, "r", encoding="utf-8") as f:
                links = [l.strip() for l in f if l.strip().startswith("http")]
        if links:
            self.url_text.insert("end", "\n" + "\n".join(links))
            self.log(f"Đã import {len(links)} link từ file.")
        else:
            messagebox.showwarning("Không tìm thấy link", "File không chứa link hợp lệ (bắt đầu bằng http).")

    def pick_output_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.out_dir_var.set(d)

    def get_urls(self):
        raw = self.url_text.get("1.0", "end")
        urls = [l.strip() for l in raw.splitlines() if l.strip() and not l.strip().startswith("#")]
        return urls

    # ---------- Template manager ----------
    def open_template_manager(self):
        TemplateManager(self)

    def refresh_templates(self):
        self.templates = tpl_store.load_templates()
        names = list(self.templates.keys())
        self.template_combo["values"] = names
        if names and self.template_var.get() not in names:
            self.template_var.set(names[0])

    # ---------- Batch run ----------
    def start_batch(self):
        urls = self.get_urls()
        if not urls:
            messagebox.showwarning("Chưa có link", "Vui lòng nhập ít nhất 1 link video.")
            return
        template = self.templates.get(self.template_var.get())
        if template is None:
            messagebox.showwarning("Chưa chọn mẫu", "Vui lòng chọn 1 mẫu edit.")
            return
        resolution_key = self.res_var.get()
        out_dir = self.out_dir_var.get()
        os.makedirs(out_dir, exist_ok=True)
        self.start_btn.configure(state="disabled")
        t = threading.Thread(
            target=self._run_pipeline,
            args=(urls, template, resolution_key, out_dir, self.sub_enabled_var.get()),
            daemon=True,
        )
        t.start()

    def _run_pipeline(self, urls, template, resolution_key, out_dir, want_sub):
        try:
            os.makedirs(WORK_DIR, exist_ok=True)
            self.log(f"=== Bắt đầu: {len(urls)} video ===")
            downloaded = download_videos(urls, WORK_DIR, log_fn=self.log)
            if not downloaded:
                self.log("Không tải được video nào. Dừng lại.")
                return

            for i, src_path in enumerate(downloaded, start=1):
                self.log(f"--- Edit video {i}/{len(downloaded)}: {os.path.basename(src_path)} ---")
                srt_path = None
                if want_sub:
                    srt_path = os.path.join(WORK_DIR, f"sub_{i:03d}.srt")
                    result = generate_srt(src_path, srt_path, log_fn=self.log)
                    srt_path = result

                out_name = f"edited_{i:03d}.mp4"
                out_path = os.path.join(out_dir, out_name)
                try:
                    edit_video(src_path, template, resolution_key, out_path, srt_path=srt_path, log_fn=self.log)
                    self.log(f"  ✓ Hoàn tất: {out_path}")
                except Exception as e:
                    self.log(f"  ✗ Lỗi khi edit video này: {e}")

            self.log("=== XONG TẤT CẢ ===")
            messagebox.showinfo("Hoàn tất", f"Đã xử lý xong. File nằm trong:\n{out_dir}")
        finally:
            self.start_btn.configure(state="normal")


class TemplateManager(tk.Toplevel):
    """Cửa sổ quản lý & chỉnh sửa mẫu edit (watermark, intro/outro, nhạc, sub, hiệu ứng)."""

    def __init__(self, master: App):
        super().__init__(master)
        self.master_app = master
        self.title("Quản lý mẫu edit")
        self.geometry("520x560")
        self.templates = tpl_store.load_templates()

        ttk.Label(self, text="Chọn mẫu để sửa, hoặc tạo mẫu mới:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ttk.Frame(self)
        row.pack(fill="x", padx=10)
        self.name_var = tk.StringVar(value=list(self.templates.keys())[0] if self.templates else "")
        self.combo = ttk.Combobox(row, textvariable=self.name_var, values=list(self.templates.keys()), state="readonly")
        self.combo.pack(side="left", fill="x", expand=True)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.load_form())
        ttk.Button(row, text="+ Mẫu mới", command=self.new_template).pack(side="left", padx=6)
        ttk.Button(row, text="Xóa mẫu", command=self.delete_template).pack(side="left")

        form = ttk.Frame(self, padding=10)
        form.pack(fill="both", expand=True)
        self.vars = {}

        def file_row(label, key, r):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", pady=3)
            v = tk.StringVar()
            ttk.Entry(form, textvariable=v, width=32).grid(row=r, column=1, pady=3)
            ttk.Button(form, text="Chọn file...", command=lambda: v.set(filedialog.askopenfilename() or v.get())).grid(row=r, column=2, padx=4)
            self.vars[key] = v

        def check_row(label, key, r, col=0):
            v = tk.BooleanVar()
            ttk.Checkbutton(form, text=label, variable=v).grid(row=r, column=col, sticky="w", pady=3)
            self.vars[key] = v

        def num_row(label, key, r):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", pady=3)
            v = tk.StringVar()
            ttk.Entry(form, textvariable=v, width=10).grid(row=r, column=1, sticky="w", pady=3)
            self.vars[key] = v

        check_row("Bật watermark/logo", "wm_enabled", 0)
        file_row("  File ảnh watermark:", "wm_path", 1)
        num_row("  Độ mờ (0-1):", "wm_opacity", 2)
        ttk.Label(form, text="  Vị trí:").grid(row=3, column=0, sticky="w")
        self.vars["wm_position"] = tk.StringVar(value="bottom-right")
        ttk.Combobox(form, textvariable=self.vars["wm_position"], values=["top-left", "top-right", "bottom-left", "bottom-right", "center"], state="readonly", width=15).grid(row=3, column=1, sticky="w")

        check_row("Bật intro", "intro_enabled", 4)
        file_row("  File video intro:", "intro_path", 5)
        check_row("Bật outro", "outro_enabled", 6)
        file_row("  File video outro:", "outro_path", 7)

        check_row("Bật nhạc nền", "music_enabled", 8)
        file_row("  File nhạc:", "music_path", 9)
        num_row("  Âm lượng nhạc nền (0-1):", "music_volume", 10)

        check_row("Bật phụ đề (chèn khi có sẵn/đã tạo)", "sub_enabled", 11)

        check_row("Hiệu ứng fade in/out", "fx_fade", 12)
        check_row("Hiệu ứng zoom nhẹ (Ken Burns)", "fx_zoom", 13)
        num_row("Tốc độ phát (1.0 = bình thường):", "fx_speed", 14)

        ttk.Button(self, text="💾 Lưu mẫu", command=self.save_template).pack(pady=10)

        if self.templates:
            self.load_form()

    def load_form(self):
        t = self.templates.get(self.name_var.get(), tpl_store.new_blank_template())
        self.vars["wm_enabled"].set(t["watermark"]["enabled"])
        self.vars["wm_path"].set(t["watermark"]["path"])
        self.vars["wm_opacity"].set(str(t["watermark"]["opacity"]))
        self.vars["wm_position"].set(t["watermark"]["position"])
        self.vars["intro_enabled"].set(t["intro"]["enabled"])
        self.vars["intro_path"].set(t["intro"]["path"])
        self.vars["outro_enabled"].set(t["outro"]["enabled"])
        self.vars["outro_path"].set(t["outro"]["path"])
        self.vars["music_enabled"].set(t["bg_music"]["enabled"])
        self.vars["music_path"].set(t["bg_music"]["path"])
        self.vars["music_volume"].set(str(t["bg_music"]["volume"]))
        self.vars["sub_enabled"].set(t["subtitle"]["enabled"])
        self.vars["fx_fade"].set(t["effects"]["fade_in_out"])
        self.vars["fx_zoom"].set(t["effects"]["zoom_ken_burns"])
        self.vars["fx_speed"].set(str(t["effects"]["speed"]))

    def new_template(self):
        name = simpledialog.askstring("Mẫu mới", "Tên mẫu mới:")
        if not name:
            return
        self.templates[name] = tpl_store.new_blank_template()
        self.combo["values"] = list(self.templates.keys())
        self.name_var.set(name)
        self.load_form()

    def delete_template(self):
        name = self.name_var.get()
        if name and messagebox.askyesno("Xóa mẫu", f"Xóa mẫu '{name}'?"):
            tpl_store.delete_template(name)
            self.templates = tpl_store.load_templates()
            self.combo["values"] = list(self.templates.keys())
            if self.templates:
                self.name_var.set(list(self.templates.keys())[0])
                self.load_form()
            self.master_app.refresh_templates()

    def save_template(self):
        name = self.name_var.get()
        if not name:
            messagebox.showwarning("Thiếu tên", "Hãy đặt tên cho mẫu trước.")
            return
        try:
            cfg = {
                "trim_start": 0, "trim_end": 0,
                "watermark": {
                    "enabled": self.vars["wm_enabled"].get(),
                    "path": self.vars["wm_path"].get(),
                    "position": self.vars["wm_position"].get(),
                    "opacity": float(self.vars["wm_opacity"].get() or 0.7),
                    "scale": 0.15,
                },
                "intro": {"enabled": self.vars["intro_enabled"].get(), "path": self.vars["intro_path"].get()},
                "outro": {"enabled": self.vars["outro_enabled"].get(), "path": self.vars["outro_path"].get()},
                "bg_music": {
                    "enabled": self.vars["music_enabled"].get(),
                    "path": self.vars["music_path"].get(),
                    "volume": float(self.vars["music_volume"].get() or 0.2),
                },
                "subtitle": {"enabled": self.vars["sub_enabled"].get(), "font_size": 42, "color": "white", "position": "bottom"},
                "effects": {
                    "fade_in_out": self.vars["fx_fade"].get(),
                    "zoom_ken_burns": self.vars["fx_zoom"].get(),
                    "speed": float(self.vars["fx_speed"].get() or 1.0),
                },
            }
        except ValueError:
            messagebox.showerror("Lỗi", "Các ô số (độ mờ, âm lượng, tốc độ) phải là số hợp lệ.")
            return
        tpl_store.upsert_template(name, cfg)
        self.master_app.refresh_templates()
        messagebox.showinfo("Đã lưu", f"Đã lưu mẫu '{name}'.")
