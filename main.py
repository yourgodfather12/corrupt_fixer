import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageFile
import concurrent.futures
import threading

# Increase the maximum image file size limit
Image.MAX_IMAGE_PIXELS = None

class GUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image and Video Repair Tool")
        self.geometry("800x600")
        self.configure(bg="black")
        self.resizable(True, True)
        self.selected_folder = ""

        # Create a label to display the current folder being processed
        self.folder_label = tk.Label(self, text="", font=("Poppins", 14), bg="black", fg="white")
        self.folder_label.pack(pady=10)

        # Create a status label to display current processing status
        self.status_label = tk.Label(self, text="", font=("Poppins", 12), bg="black", fg="white")
        self.status_label.pack(pady=10)

        # Create a progress bar to show the progress of the repair process
        self.progress_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=600, mode="determinate", style="success.Horizontal.TProgressbar")
        self.progress_bar.pack(pady=20)

        # Create a log text area to display feedback and errors
        self.log_text = tk.Text(self, height=10, width=80, wrap="word", bg="black", fg="white", font=("Poppins", 12))
        self.log_text.pack(pady=10)

        # Redirect stdout and stderr to the log text area
        self.stdout_orig = sys.stdout
        self.stderr_orig = sys.stderr
        sys.stdout = TextRedirector(self.log_text, "stdout")
        sys.stderr = TextRedirector(self.log_text, "stderr")

        # Create a button to select a folder for scanning
        self.select_folder_button = tk.Button(self, text="Select Folder", command=self.select_folder, bg="#007acc", fg="white", font=("Poppins", 14))
        self.select_folder_button.pack(pady=10)

        # Create a button to start the repair process
        self.start_button = tk.Button(self, text="Start Repair", command=self.start_repair, bg="#007acc", fg="white", font=("Poppins", 14), state=tk.DISABLED)
        self.start_button.pack(pady=10)

        # Style the progress bar
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("success.Horizontal.TProgressbar", foreground='green', background='green')

    def select_folder(self):
        # Prompt user to select a folder for scanning
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.selected_folder = folder_path
            self.folder_label.config(text=f"Selected folder: {folder_path}")
            self.start_button.config(state=tk.NORMAL)

    def scan_folder(self):
        # Reset progress bar, status label, and log text
        self.progress_bar["value"] = 0
        self.status_label.config(text="Scanning files...")
        self.log_text.delete(1.0, tk.END)

        # Walk through the folder and its subfolders to find images
        total_files = sum(len(files) for _, _, files in os.walk(self.selected_folder))
        processed_files = 0
        corrupted_files = 0

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for root, dirs, files in os.walk(self.selected_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.is_supported_format(file_path):
                        futures.append(executor.submit(self.repair_file, file_path))
                        processed_files += 1

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.log_text.insert(tk.END, f"Error repairing file: {e}\n")
                    corrupted_files += 1

        # Update progress bar and display message
        self.progress_bar["value"] = 100
        self.status_label.config(text=f"Scan complete. Found {processed_files - corrupted_files} files. {corrupted_files} files could not be repaired.")

    def start_repair(self):
        # Disable the start button during repair process
        self.start_button.config(state=tk.DISABLED)

        # Start the repair process
        self.scan_folder_thread = threading.Thread(target=self.scan_folder)
        self.scan_folder_thread.start()

    def repair_file(self, file_path):
        # Use the PIL library to repair the image
        try:
            with Image.open(file_path) as img:
                img = img.copy()
                if not img.verify():
                    img = img.convert("RGB")
                    img.save(file_path)
        except Exception as e:
            raise e

    def is_supported_format(self, file_path):
        # Check if the file extension is supported
        _, ext = os.path.splitext(file_path)
        if ext.lower() in [".jpg", ".jpeg", ".png"]:
            return True
        else:
            return False

class TextRedirector:
    def __init__(self, text_widget, tag):
        self.text_widget = text_widget
        self.tag = tag

    def write(self, str):
        self.text_widget.insert(tk.END, str, (self.tag,))
        self.text_widget.see(tk.END)

    def flush(self):
        pass

if __name__ == "__main__":
    app = GUI()
    app.mainloop()
