# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import sys
import threading
import platform
import wave
import struct
import math

# 核心脚本文件名 (必须与实际保存的文件名一致)
CORE_SCRIPT_NAME = "smpte_noise.py"

class PinkNoiseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SMPTE ST 2095-1 Pink Noise Generator")
        self.root.geometry("520x600") # 增加高度以容纳统计信息
        
        # 样式设置
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 10))
        style.configure('TLabel', font=('Arial', 10))
        style.configure('Result.TLabel', font=('Arial', 11, 'bold'), foreground="#2c3e50")
        
        # 主框架
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 1. 采样率 ---
        ttk.Label(main_frame, text="1. Sample Rate:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.samplerate_var = tk.StringVar(value="48000")
        sr_frame = ttk.Frame(main_frame)
        sr_frame.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(sr_frame, text="48 kHz (Default)", variable=self.samplerate_var, value="48000").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(sr_frame, text="96 kHz", variable=self.samplerate_var, value="96000").pack(side=tk.LEFT, padx=5)

        # --- 2. 时长 ---
        ttk.Label(main_frame, text="2. Duration (seconds):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.duration_var = tk.StringVar(value="10")
        ttk.Entry(main_frame, textvariable=self.duration_var, width=15).grid(row=1, column=1, sticky=tk.W, pady=5)

        # --- 3. 声道数 ---
        ttk.Label(main_frame, text="3. Channel Count:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.channel_var = tk.StringVar(value="1")
        ttk.Entry(main_frame, textvariable=self.channel_var, width=15).grid(row=2, column=1, sticky=tk.W, pady=5)

        # --- 4. 文件名 ---
        ttk.Label(main_frame, text="4. Filename (no extension):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.filename_var = tk.StringVar(value="pink_noise_output")
        ttk.Entry(main_frame, textvariable=self.filename_var, width=30).grid(row=3, column=1, sticky=tk.W, pady=5)

        # --- 5. 输出位置 ---
        ttk.Label(main_frame, text="5. Output Folder:").grid(row=4, column=0, sticky=tk.W, pady=5)
        
        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        self.output_dir_var = tk.StringVar(value=os.getcwd()) # 默认为当前目录
        self.path_entry = ttk.Entry(path_frame, textvariable=self.output_dir_var, width=30)
        self.path_entry.pack(side=tk.LEFT)
        
        ttk.Button(path_frame, text="Browse...", command=self.select_directory).pack(side=tk.LEFT, padx=5)

        # --- 分割线 ---
        ttk.Separator(main_frame, orient='horizontal').grid(row=5, column=0, columnspan=2, sticky="ew", pady=15)

        # --- 生成按钮 ---
        self.generate_btn = ttk.Button(main_frame, text="Generate Audio", command=self.start_generation_thread)
        self.generate_btn.grid(row=6, column=0, columnspan=2, pady=(5, 5))

        # --- 打开文件夹按钮 ---
        self.open_folder_btn = ttk.Button(main_frame, text="Open Output Folder", command=self.open_current_folder, state=tk.DISABLED)
        self.open_folder_btn.grid(row=7, column=0, columnspan=2, pady=5)

        # --- 结果统计显示 (新增功能) ---
        self.result_stats_var = tk.StringVar(value="Measurement: --")
        self.stats_label = ttk.Label(main_frame, textvariable=self.result_stats_var, style='Result.TLabel')
        self.stats_label.grid(row=8, column=0, columnspan=2, pady=(10, 0))

        # --- 波形画布 ---
        self.canvas_width = 480
        self.canvas_height = 80
        self.waveform_canvas = tk.Canvas(main_frame, width=self.canvas_width, height=self.canvas_height, bg="#f0f0f0", highlightthickness=1, highlightbackground="#cccccc")
        self.waveform_canvas.grid(row=9, column=0, columnspan=2, pady=(5, 10))
        # 占位符文本
        self.waveform_text = self.waveform_canvas.create_text(self.canvas_width//2, self.canvas_height//2, text="Waveform Preview", fill="gray")

        # --- 底部状态栏 ---
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var, foreground="gray").grid(row=10, column=0, columnspan=2, pady=5)

    def select_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)

    def open_current_folder(self):
        """打开当前输出目录"""
        path = self.output_dir_var.get()
        if not os.path.isdir(path):
            messagebox.showerror("Error", "Directory does not exist.")
            return

        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", path])
            else:  # Linux
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def draw_waveform(self, file_path):
        """读取 WAV 文件并在画布上绘制简化波形"""
        self.waveform_canvas.delete("all") 
        self.waveform_canvas.create_text(self.canvas_width//2, self.canvas_height//2, text="Loading...", fill="gray")
        self.root.update_idletasks() 

        try:
            with wave.open(file_path, 'rb') as wf:
                n_channels = wf.getnchannels()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                sampwidth = wf.getsampwidth()
                
                # 降采样步长
                step = max(1, n_frames // self.canvas_width)
                
                center_y = self.canvas_height / 2
                max_height = self.canvas_height / 2 - 2
                
                points = []
                
                # 限制预览读取量 (前30秒)
                frames_to_read = min(n_frames, framerate * 30) 
                
                raw_bytes = wf.readframes(frames_to_read)
                
                self.waveform_canvas.delete("all")
                
                # 绘制中心线
                self.waveform_canvas.create_line(0, center_y, self.canvas_width, center_y, fill="#dddddd")

                for x in range(0, self.canvas_width):
                    frame_index = int(x * step)
                    if frame_index >= frames_to_read:
                        break
                        
                    byte_index = frame_index * sampwidth * n_channels
                    
                    if byte_index + sampwidth > len(raw_bytes):
                        break

                    sample_bytes = raw_bytes[byte_index : byte_index + sampwidth]
                    
                    val = 0
                    if sampwidth == 3: # 24-bit
                        val = int.from_bytes(sample_bytes, byteorder='little', signed=True)
                        max_val = 2**23 - 1
                    elif sampwidth == 2: # 16-bit
                        val = int.from_bytes(sample_bytes, byteorder='little', signed=True)
                        max_val = 2**15 - 1
                    elif sampwidth == 1: # 8-bit
                        val = int.from_bytes(sample_bytes, byteorder='little', signed=False) - 128
                        max_val = 127
                    else:
                        continue 

                    normalized_h = (val / max_val) * max_height
                    points.append(x)
                    points.append(center_y - normalized_h)
                
                if len(points) > 2:
                    # 绘制波形 (SMPTE Pink 风格颜色)
                    self.waveform_canvas.create_line(points, fill="#FF0080", width=1)
                    
        except Exception as e:
            print(f"Waveform error: {e}")
            self.waveform_canvas.delete("all")
            self.waveform_canvas.create_text(self.canvas_width//2, self.canvas_height//2, text="Preview unavailable", fill="red")

    def start_generation_thread(self):
        t = threading.Thread(target=self.generate_noise)
        t.start()

    def generate_noise(self):
        # 1. 验证
        try:
            duration = int(self.duration_var.get())
            channels = int(self.channel_var.get())
            filename = self.filename_var.get().strip()
            output_dir = self.output_dir_var.get()
            
            if not filename:
                messagebox.showerror("Error", "Please enter a filename.")
                return
            
            if not filename.lower().endswith(".wav"):
                filename += ".wav"
                
            full_output_path = os.path.join(output_dir, filename)
            
        except ValueError:
            messagebox.showerror("Error", "Duration and Channel Count must be integers.")
            return

        # 2. 检查脚本
        if not os.path.exists(CORE_SCRIPT_NAME):
            messagebox.showerror("Error", f"Core script not found: {CORE_SCRIPT_NAME}\nPlease ensure the original code is saved with this name in the same directory.")
            return

        # 3. 构建命令
        cmd = [sys.executable, CORE_SCRIPT_NAME]
        
        if self.samplerate_var.get() == "96000":
            cmd.append("-9")
        
        cmd.append("-d")
        cmd.append(str(duration))
        cmd.append("-c")
        cmd.append(str(channels))
        cmd.append(full_output_path)

        # 4. 执行
        self.status_var.set("Generating, please wait...")
        self.result_stats_var.set("Generating...") # 重置统计显示
        self.waveform_canvas.delete("all")
        self.waveform_canvas.create_text(self.canvas_width//2, self.canvas_height//2, text="Generating...", fill="blue")
        
        self.generate_btn.config(state=tk.DISABLED)
        self.open_folder_btn.config(state=tk.DISABLED)
        
        try:
            # 捕获输出
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                self.status_var.set(f"Success: {filename}")
                self.open_folder_btn.config(state=tk.NORMAL)
                
                # --- 提取并显示 RMS ---
                output_text = result.stdout.strip()
                # 原始脚本输出通常是: "10.00 seconds, RMS (dB) = -21.50"
                # 我们尝试直接显示这行文字，或者提取其中的数值部分
                if "RMS (dB)" in output_text:
                    self.result_stats_var.set(output_text) # 直接显示脚本返回的统计行
                else:
                    self.result_stats_var.set("Measured RMS: (Check Popup)")

                # 绘制波形和弹窗
                self.root.after(0, lambda: self.draw_waveform(full_output_path))
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Generation Complete!\nFile: {filename}\n\n{output_text}"))
                
            else:
                messagebox.showerror("Generation Failed", f"Script Error:\n{result.stderr}")
                self.status_var.set("Generation Failed")
                self.result_stats_var.set("Error")
                self.waveform_canvas.delete("all")
                
        except Exception as e:
            messagebox.showerror("System Error", str(e))
            self.status_var.set("System Error")
            self.result_stats_var.set("Error")
            self.waveform_canvas.delete("all")
        finally:
            self.generate_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = PinkNoiseApp(root)
    root.mainloop()