import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image

class TextRedirector:
    def __init__(self, text_widget, tag):
        self.text_widget = text_widget
        self.tag = tag

    def write(self, text):
        self.text_widget.insert(tk.END, text, (self.tag,))
        self.text_widget.see(tk.END)

    def flush(self):
        pass

class ImageRepairTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Repair Tool")
        self.geometry("800x600")
        self.configure(bg="white")
        self.resizable(True, True)
        self.selected_folder = ""
        self.repairing = False

        self.create_widgets()

    def create_widgets(self):
        self.folder_label = tk.Label(self, text="", font=("Arial", 12), bg="white", fg="black")
        self.folder_label.pack(pady=10)

        self.status_label = tk.Label(self, text="", font=("Arial", 12), bg="white", fg="black")
        self.status_label.pack(pady=10)

        self.progress_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=600, mode="determinate")
        self.progress_bar.pack(pady=20)

        self.log_text = tk.Text(self, height=10, width=80, wrap="word", bg="white", fg="black", font=("Arial", 10))
        self.log_text.pack(pady=10)

        sys.stdout = TextRedirector(self.log_text, "stdout")
        sys.stderr = TextRedirector(self.log_text, "stderr")

        self.select_folder_button = tk.Button(self, text="Select Folder", command=self.select_folder)
        self.select_folder_button.pack(pady=10)

        self.start_button = tk.Button(self, text="Start Repair", command=self.start_repair, state=tk.DISABLED)
        self.start_button.pack(pady=10)

        self.preview_button = tk.Button(self, text="Preview Repaired Images", command=self.preview_images, state=tk.DISABLED)
        self.preview_button.pack(pady=5)

        self.language_menu = tk.Menu(self, tearoff=0)
        self.language_menu.add_command(label="English", command=lambda: self.change_language("English"))
        self.language_menu.add_command(label="Spanish", command=lambda: self.change_language("Spanish"))
        self.language_menu.add_command(label="French", command=lambda: self.change_language("French"))

        self.language_menu_button = tk.Menubutton(self, text="Select Language", menu=self.language_menu)
        self.language_menu_button.pack(pady=5)

    def change_language(self, language):
        # Code to change the language of the interface
        messagebox.showinfo("Language Changed", f"Interface language changed to {language}")

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.selected_folder = folder_path
            self.folder_label.config(text=f"Selected folder: {folder_path}")
            self.start_button.config(state=tk.NORMAL)

    def start_repair(self):
        if self.repairing:
            return
        self.repairing = True
        self.start_button.config(state=tk.DISABLED)
        self.scan_folder()

    def scan_folder(self):
        self.progress_bar["value"] = 0
        self.status_label.config(text="Scanning files...")
        self.log_text.delete(1.0, tk.END)

        total_files = sum(len(files) for _, _, files in os.walk(self.selected_folder))
        processed_files = 0
        repaired_files = 0
        corrupted_files = 0

        for root, _, files in os.walk(self.selected_folder):
            for file in files:
                file_path = os.path.normpath(os.path.join(root, file))
                if self.is_supported_format(file_path):
                    try:
                        result = self.repair_file(file_path)
                        if result[1] == "Success":
                            repaired_files += 1
                        else:
                            corrupted_files += 1
                            error_message = f"Error repairing file '{result[0]}': {result[1]}"
                            self.log_text.insert(tk.END, error_message + "\n")
                    except Exception as e:
                        self.log_text.insert(tk.END, f"Error: {e}\n")
                        corrupted_files += 1
                    processed_files += 1
                    self.update_progress(processed_files, total_files)

        self.progress_bar["value"] = 100
        self.status_label.config(
            text=f"Repair complete. Repaired {repaired_files} out of {processed_files} files. {corrupted_files} files could not be repaired.")
        self.log_text.see(tk.END)
        self.repairing = False
        self.preview_button.config(state=tk.NORMAL)

    def is_supported_format(self, file_path):
        _, ext = os.path.splitext(file_path)
        supported_formats = [".jpg", ".jpeg", ".png", ".heif", ".heic"]
        return ext.lower() in supported_formats

    def repair_file(self, file_path):
        with Image.open(file_path) as img:
            img = img.copy()

            if not img.verify():
                img = img.convert("RGB")
                img.save(file_path)
                return file_path, "Success"
            else:
                return file_path, "Image already valid"

    def update_progress(self, processed_files, total_files):
        self.progress_bar["value"] = (processed_files / total_files) * 100
        self.status_label.config(text=f"Repairing files... ({processed_files}/{total_files})")

    def preview_images(self):
        # Code to preview repaired images
        messagebox.showinfo("Preview", "Preview functionality will be implemented in the next version.")

if __name__ == "__main__":
    app = ImageRepairTool()
    app.mainloop()
