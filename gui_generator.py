# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import sys
import threading
import platform

# The filename of the original script you provided
CORE_SCRIPT_NAME = "smpte_noise.py"

class PinkNoiseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SMPTE ST 2095-1 Pink Noise Generator")
        self.root.geometry("520x420") # Increased height slightly
        
        # Style configuration
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 10))
        style.configure('TLabel', font=('Arial', 10))
        
        # Main container
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 1. Sample Rate ---
        ttk.Label(main_frame, text="1. Sample Rate:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.samplerate_var = tk.StringVar(value="48000")
        sr_frame = ttk.Frame(main_frame)
        sr_frame.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(sr_frame, text="48 kHz (Default)", variable=self.samplerate_var, value="48000").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(sr_frame, text="96 kHz", variable=self.samplerate_var, value="96000").pack(side=tk.LEFT, padx=5)

        # --- 2. Duration ---
        ttk.Label(main_frame, text="2. Duration (seconds):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.duration_var = tk.StringVar(value="10")
        ttk.Entry(main_frame, textvariable=self.duration_var, width=15).grid(row=1, column=1, sticky=tk.W, pady=5)

        # --- 3. Channels ---
        ttk.Label(main_frame, text="3. Channel Count:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.channel_var = tk.StringVar(value="1")
        ttk.Entry(main_frame, textvariable=self.channel_var, width=15).grid(row=2, column=1, sticky=tk.W, pady=5)

        # --- 4. Filename ---
        ttk.Label(main_frame, text="4. Filename (no extension):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.filename_var = tk.StringVar(value="pink_noise_output")
        ttk.Entry(main_frame, textvariable=self.filename_var, width=30).grid(row=3, column=1, sticky=tk.W, pady=5)

        # --- 5. Output Location ---
        ttk.Label(main_frame, text="5. Output Folder:").grid(row=4, column=0, sticky=tk.W, pady=5)
        
        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        self.output_dir_var = tk.StringVar(value=os.getcwd()) # Default to current directory
        self.path_entry = ttk.Entry(path_frame, textvariable=self.output_dir_var, width=30)
        self.path_entry.pack(side=tk.LEFT)
        
        ttk.Button(path_frame, text="Browse...", command=self.select_directory).pack(side=tk.LEFT, padx=5)

        # --- Separator ---
        ttk.Separator(main_frame, orient='horizontal').grid(row=5, column=0, columnspan=2, sticky="ew", pady=15)

        # --- Generate Button ---
        self.generate_btn = ttk.Button(main_frame, text="Generate Audio", command=self.start_generation_thread)
        self.generate_btn.grid(row=6, column=0, columnspan=2, pady=(10, 5))

        # --- Open Folder Button (New Feature) ---
        self.open_folder_btn = ttk.Button(main_frame, text="Open Output Folder", command=self.open_current_folder, state=tk.DISABLED)
        self.open_folder_btn.grid(row=7, column=0, columnspan=2, pady=5)

        # --- Status Bar ---
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var, foreground="gray").grid(row=8, column=0, columnspan=2, pady=5)

    def select_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)

    def open_current_folder(self):
        """Opens the directory defined in output_dir_var in the OS file explorer."""
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

    def start_generation_thread(self):
        # Use a thread to prevent the GUI from freezing during generation
        t = threading.Thread(target=self.generate_noise)
        t.start()

    def generate_noise(self):
        # 1. Validation
        try:
            duration = int(self.duration_var.get())
            channels = int(self.channel_var.get())
            filename = self.filename_var.get().strip()
            output_dir = self.output_dir_var.get()
            
            if not filename:
                messagebox.showerror("Error", "Please enter a filename.")
                return
            
            # Ensure extension is .wav
            if not filename.lower().endswith(".wav"):
                filename += ".wav"
                
            full_output_path = os.path.join(output_dir, filename)
            
        except ValueError:
            messagebox.showerror("Error", "Duration and Channel Count must be integers.")
            return

        # 2. Check for core script
        if not os.path.exists(CORE_SCRIPT_NAME):
            messagebox.showerror("Error", f"Core script not found: {CORE_SCRIPT_NAME}\nPlease ensure the original code is saved with this name in the same directory.")
            return

        # 3. Build command
        # python script.py [-9] [-c channels] [-d duration] <outfile>
        cmd = [sys.executable, CORE_SCRIPT_NAME]
        
        # Sample Rate
        if self.samplerate_var.get() == "96000":
            cmd.append("-9")
        
        # Duration
        cmd.append("-d")
        cmd.append(str(duration))
        
        # Channels
        cmd.append("-c")
        cmd.append(str(channels))
        
        # Output Path
        cmd.append(full_output_path)

        # 4. Execute
        self.status_var.set("Generating, please wait...")
        self.generate_btn.config(state=tk.DISABLED)
        self.open_folder_btn.config(state=tk.DISABLED) # Disable open button while generating
        
        try:
            # Run the external script
            # encoding='utf-8' ensures we can handle non-ASCII characters if printed by the script
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                messagebox.showinfo("Success", f"Generation Complete!\nFile location: {full_output_path}\n\nStats:\n{result.stdout}")
                self.status_var.set(f"Success: {filename}")
                # Enable the Open Folder button on success
                self.open_folder_btn.config(state=tk.NORMAL)
            else:
                messagebox.showerror("Generation Failed", f"Script Error:\n{result.stderr}")
                self.status_var.set("Generation Failed")
                
        except Exception as e:
            messagebox.showerror("System Error", str(e))
            self.status_var.set("System Error")
        finally:
            self.generate_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = PinkNoiseApp(root)
    root.mainloop()