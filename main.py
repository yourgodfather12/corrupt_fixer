import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, UnidentifiedImageError
import logging
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from ffmpeg import probe, Error
import cv2
import psutil
import time
from tqdm import tqdm

# Supported file extensions
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.heic', '.heiv']
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']

# Locks for thread-safe operations
lock = threading.Lock()

# Logging configuration
logging.basicConfig(filename='image_video_repair_tool.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class TextRedirector:
    def __init__(self, text_widget, tag):
        self.text_widget = text_widget
        self.tag = tag

    def write(self, text):
        self.text_widget.insert(tk.END, text, (self.tag,))
        self.text_widget.see(tk.END)

    def flush(self):
        pass


class ImageVideoRepairTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image & Video Repair Tool")
        self.geometry("800x600")
        self.configure(bg="white")
        self.resizable(True, True)
        self.selected_folder = ""
        self.repairing = False
        self.language_texts = {}
        self.current_language = "English"
        self.stop_process = False  # Variable to track if user wants to abort the repair
        self.backup_enabled = tk.BooleanVar(value=True)  # Option to toggle backups

        self.load_language_texts()
        self.create_widgets()
        self.setup_logging()

    def load_language_texts(self):
        """ Load texts for different languages from JSON """
        try:
            with open("language_texts.json", "r") as file:
                self.language_texts = json.load(file)
        except FileNotFoundError:
            self.language_texts = {"English": {}}
            logging.error("Language file not found, defaulting to English.")

    def get_text(self, key):
        """ Retrieve the correct language string """
        return self.language_texts.get(self.current_language, {}).get(key, key)

    def setup_logging(self):
        """ Setup logging for the application """
        logging.basicConfig(filename='image_video_repair_tool.log', level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

    def create_widgets(self):
        """ Initialize GUI widgets """
        self.create_labels()
        self.create_progress_bar()
        self.create_text_log()
        self.create_buttons()
        self.create_language_menu()
        self.create_file_type_options()

        sys.stdout = TextRedirector(self.log_text, "stdout")
        sys.stderr = TextRedirector(self.log_text, "stderr")

    def create_labels(self):
        """ Create labels for the GUI """
        self.folder_label = tk.Label(self, text="", font=("Arial", 12), bg="white", fg="black")
        self.folder_label.pack(pady=10)

        self.status_label = tk.Label(self, text="", font=("Arial", 12), bg="white", fg="black")
        self.status_label.pack(pady=10)

    def create_progress_bar(self):
        """ Create the progress bar widget """
        self.progress_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=600, mode="determinate")
        self.progress_bar.pack(pady=20)

    def create_text_log(self):
        """ Create the text log widget to show process output """
        self.log_text = tk.Text(self, height=10, width=80, wrap="word", bg="white", fg="black", font=("Arial", 10))
        self.log_text.pack(pady=10)

    def create_buttons(self):
        """ Create control buttons """
        self.select_folder_button = tk.Button(self, text=self.get_text("Select Folder"), command=self.select_folder)
        self.select_folder_button.pack(pady=10)

        self.start_button = tk.Button(self, text=self.get_text("Start Repair"), command=self.start_repair, state=tk.DISABLED)
        self.start_button.pack(pady=10)

        self.preview_button = tk.Button(self, text=self.get_text("Preview Repaired Files"), command=self.preview_files, state=tk.DISABLED)
        self.preview_button.pack(pady=5)

        self.abort_button = tk.Button(self, text=self.get_text("Abort Repair"), command=self.abort_repair, state=tk.DISABLED)
        self.abort_button.pack(pady=5)

        self.backup_checkbox = tk.Checkbutton(self, text="Enable Backup", variable=self.backup_enabled)
        self.backup_checkbox.pack(pady=5)

    def create_language_menu(self):
        """ Create a language selection menu """
        self.language_menu = tk.Menu(self, tearoff=0)
        for language in self.language_texts.keys():
            self.language_menu.add_command(label=language, command=lambda lang=language: self.change_language(lang))

        self.language_menu_button = tk.Menubutton(self, text=self.get_text("Select Language"), menu=self.language_menu)
        self.language_menu_button.pack(pady=5)

    def create_file_type_options(self):
        """ Create options for choosing to repair only images, only videos, or both """
        self.file_type_var = tk.StringVar(value="both")
        tk.Radiobutton(self, text="Images Only", variable=self.file_type_var, value="images").pack(anchor="w")
        tk.Radiobutton(self, text="Videos Only", variable=self.file_type_var, value="videos").pack(anchor="w")
        tk.Radiobutton(self, text="Both", variable=self.file_type_var, value="both").pack(anchor="w")

    def change_language(self, language):
        """ Change the current language for the UI """
        self.current_language = language
        self.update_ui_texts()
        messagebox.showinfo(self.get_text("Language Changed"), self.get_text("Language Change Message").format(language))

    def update_ui_texts(self):
        """ Update UI texts after language change """
        self.select_folder_button.config(text=self.get_text("Select Folder"))
        self.start_button.config(text=self.get_text("Start Repair"))
        self.preview_button.config(text=self.get_text("Preview Repaired Files"))
        self.language_menu_button.config(text=self.get_text("Select Language"))
        self.abort_button.config(text=self.get_text("Abort Repair"))

    def select_folder(self):
        """ Allow the user to select a folder """
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.selected_folder = folder_path
            self.folder_label.config(text=self.get_text("Selected folder").format(folder_path))
            self.start_button.config(state=tk.NORMAL)
            self.abort_button.config(state=tk.DISABLED)

    def start_repair(self):
        """ Start the repair process """
        if self.repairing:
            return
        self.repairing = True
        self.stop_process = False
        self.start_button.config(state=tk.DISABLED)
        self.abort_button.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        threading.Thread(target=self.scan_and_repair_folder).start()

    def abort_repair(self):
        """ Gracefully abort the repair process """
        self.stop_process = True
        self.abort_button.config(state=tk.DISABLED)
        self.status_label.config(text=self.get_text("Aborting..."))

    def scan_and_repair_folder(self):
        """ Scan and repair all files in the selected folder """
        self.progress_bar["value"] = 0
        self.status_label.config(text=self.get_text("Scanning files..."))

        total_files = sum(len(files) for _, _, files in os.walk(self.selected_folder))
        processed_files = 0
        repaired_files = 0
        corrupted_files = 0

        conn = self.init_db("repair_log")  # Initialize database connection

        all_files = [os.path.join(root, file) for root, dirs, files in os.walk(self.selected_folder) for file in files]

        # Filter based on the selected file type option
        if self.file_type_var.get() == "images":
            all_files = [f for f in all_files if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS]
        elif self.file_type_var.get() == "videos":
            all_files = [f for f in all_files if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS]

        with ThreadPoolExecutor(max_workers=5) as executor:  # Controlled concurrency
            futures = []
            for file_path in all_files:
                if self.stop_process:
                    break
                ext = os.path.splitext(file_path)[1].lower()
                if ext in IMAGE_EXTENSIONS:
                    futures.append(executor.submit(self.check_and_fix_image, file_path, conn))
                elif ext in VIDEO_EXTENSIONS:
                    futures.append(executor.submit(self.check_and_fix_video, file_path, conn))

            for future in as_completed(futures):
                if self.stop_process:
                    break
                result = future.result()
                if result == "repaired":
                    repaired_files += 1
                elif result == "corrupt":
                    corrupted_files += 1
                processed_files += 1
                self.update_progress(processed_files, total_files)

        if not self.stop_process:
            self.status_label.config(text=self.get_text("Repair complete").format(repaired_files, total_files, corrupted_files))
            self.preview_button.config(state=tk.NORMAL)
        else:
            self.status_label.config(text=self.get_text("Repair aborted"))

        self.repairing = False
        self.abort_button.config(state=tk.DISABLED)

    def init_db(self, db_name):
        """ Initialize a SQLite database to log file repair status """
        db_path = os.path.join(os.getcwd(), f"{db_name}.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS file_log (
                          file_path TEXT PRIMARY KEY,
                          file_type TEXT,
                          status TEXT,
                          checksum TEXT,
                          repair_time REAL,
                          file_size INTEGER,
                          error_message TEXT)''')
        conn.commit()
        return conn

    def check_and_fix_image(self, file_path, conn):
        """ Check and fix corrupt images """
        try:
            if self.backup_enabled.get():
                self.create_backup(file_path)

            with Image.open(file_path) as img:
                img.verify()  # Check if image is valid
                checksum = self.calculate_checksum(file_path)
                self.log_file_status(conn, file_path, 'image', 'valid', checksum, None)
                return "valid"
        except UnidentifiedImageError:
            # Attempt to repair
            try:
                img = Image.open(file_path).convert('RGB')
                img.save(file_path)
                checksum = self.calculate_checksum(file_path)
                self.log_file_status(conn, file_path, 'image', 'repaired', checksum, None)
                return "repaired"
            except Exception as e:
                self.log_file_status(conn, file_path, 'image', 'corrupt', None, None, str(e))
                return "corrupt"

    def check_and_fix_video(self, file_path, conn):
        """ Check and fix corrupt videos """
        try:
            if self.backup_enabled.get():
                self.create_backup(file_path)

            probe(file_path)  # Check if video is valid using FFmpeg
            checksum = self.calculate_checksum(file_path)
            self.log_file_status(conn, file_path, 'video', 'valid', checksum, None)
            return "valid"
        except Error as e:
            self.log_file_status(conn, file_path, 'video', 'corrupt', None, None, str(e))
            return "corrupt"

    def calculate_checksum(self, file_path):
        """ Calculate a checksum for file validation """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def log_file_status(self, conn, file_path, file_type, status, checksum, repair_time, error_message=None):
        """ Log the file repair status to the database """
        cursor = conn.cursor()
        cursor.execute('''INSERT OR REPLACE INTO file_log (file_path, file_type, status, checksum, repair_time, error_message)
                          VALUES (?, ?, ?, ?, ?, ?)''', (file_path, file_type, status, checksum, repair_time, error_message))
        conn.commit()

    def update_progress(self, processed_files, total_files):
        """ Update the progress bar and status label """
        self.progress_bar["value"] = (processed_files / total_files) * 100
        self.status_label.config(text=self.get_text("Repairing files...").format(processed_files, total_files))

    def create_backup(self, file_path):
        """ Create a backup of the original file before attempting repair """
        backup_path = file_path + ".bak"
        if not os.path.exists(backup_path):
            os.rename(file_path, backup_path)

    def preview_files(self):
        """ Preview repaired files (placeholder functionality) """
        preview_window = tk.Toplevel(self)
        preview_window.title(self.get_text("Preview Window Title"))
        preview_window.geometry("800x600")
        images = [os.path.join(dp, f) for dp, dn, filenames in os.walk(self.selected_folder) for f in filenames if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS]
        if images:
            img_path = images[0]  # Just show the first image as an example
            img = Image.open(img_path)
            img.thumbnail((800, 600))
            img = tk.PhotoImage(file=img_path)
            img_label = tk.Label(preview_window, image=img)
            img_label.image = img  # Keep a reference to avoid garbage collection
            img_label.pack()


if __name__ == "__main__":
    app = ImageVideoRepairTool()
    app.mainloop()
