import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, UnidentifiedImageError
import logging
import json

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
        self.language_texts = {}
        self.current_language = "English"

        self.load_language_texts()
        self.create_widgets()
        self.setup_logging()

    def load_language_texts(self):
        with open("language_texts.json", "r") as file:
            self.language_texts = json.load(file)

    def get_text(self, key):
        return self.language_texts.get(self.current_language, {}).get(key, key)

    def setup_logging(self):
        logging.basicConfig(filename='image_repair_tool.log', level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

    def create_widgets(self):
        self.create_labels()
        self.create_progress_bar()
        self.create_text_log()
        self.create_buttons()
        self.create_language_menu()

        sys.stdout = TextRedirector(self.log_text, "stdout")
        sys.stderr = TextRedirector(self.log_text, "stderr")

    def create_labels(self):
        self.folder_label = tk.Label(self, text="", font=("Arial", 12), bg="white", fg="black")
        self.folder_label.pack(pady=10)

        self.status_label = tk.Label(self, text="", font=("Arial", 12), bg="white", fg="black")
        self.status_label.pack(pady=10)

    def create_progress_bar(self):
        self.progress_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=600, mode="determinate")
        self.progress_bar.pack(pady=20)

    def create_text_log(self):
        self.log_text = tk.Text(self, height=10, width=80, wrap="word", bg="white", fg="black", font=("Arial", 10))
        self.log_text.pack(pady=10)

    def create_buttons(self):
        self.select_folder_button = tk.Button(self, text=self.get_text("Select Folder"), command=self.select_folder)
        self.select_folder_button.pack(pady=10)

        self.start_button = tk.Button(self, text=self.get_text("Start Repair"), command=self.start_repair, state=tk.DISABLED)
        self.start_button.pack(pady=10)

        self.preview_button = tk.Button(self, text=self.get_text("Preview Repaired Images"), command=self.preview_images, state=tk.DISABLED)
        self.preview_button.pack(pady=5)

    def create_language_menu(self):
        self.language_menu = tk.Menu(self, tearoff=0)
        for language in self.language_texts.keys():
            self.language_menu.add_command(label=language, command=lambda lang=language: self.change_language(lang))

        self.language_menu_button = tk.Menubutton(self, text=self.get_text("Select Language"), menu=self.language_menu)
        self.language_menu_button.pack(pady=5)

    def change_language(self, language):
        self.current_language = language
        self.update_ui_texts()
        messagebox.showinfo(self.get_text("Language Changed"), self.get_text("Language Change Message").format(language))

    def update_ui_texts(self):
        self.select_folder_button.config(text=self.get_text("Select Folder"))
        self.start_button.config(text=self.get_text("Start Repair"))
        self.preview_button.config(text=self.get_text("Preview Repaired Images"))
        self.language_menu_button.config(text=self.get_text("Select Language"))

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.selected_folder = folder_path
            self.folder_label.config(text=self.get_text("Selected folder").format(folder_path))
            self.start_button.config(state=tk.NORMAL)

    def start_repair(self):
        if self.repairing:
            return
        self.repairing = True
        self.start_button.config(state=tk.DISABLED)
        threading.Thread(target=self.scan_folder).start()

    def scan_folder(self):
        self.progress_bar["value"] = 0
        self.status_label.config(text=self.get_text("Scanning files..."))
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
                            error_message = f"{self.get_text('Error repairing file')} '{result[0]}': {result[1]}"
                            logging.error(error_message)
                            self.log_text.insert(tk.END, error_message + "\n")
                    except UnidentifiedImageError:
                        error_message = self.get_text("Error: Not a valid image file").format(file_path)
                        logging.error(error_message)
                        self.log_text.insert(tk.END, error_message + "\n")
                        corrupted_files += 1
                    except Exception as e:
                        error_message = f"Error: {e}"
                        logging.error(error_message)
                        self.log_text.insert(tk.END, error_message + "\n")
                        corrupted_files += 1
                    processed_files += 1
                    self.update_progress(processed_files, total_files)

        self.progress_bar["value"] = 100
        self.status_label.config(
            text=self.get_text("Repair complete").format(repaired_files, processed_files, corrupted_files))
        logging.info(self.get_text("Repair complete").format(repaired_files, processed_files, corrupted_files))
        self.log_text.see(tk.END)
        self.repairing = False
        self.preview_button.config(state=tk.NORMAL)

    def is_supported_format(self, file_path):
        _, ext = os.path.splitext(file_path)
        supported_formats = [".jpg", ".jpeg", ".png", ".heif", ".heic"]
        return ext.lower() in supported_formats

    def repair_file(self, file_path):
        with Image.open(file_path) as img:
            try:
                img.verify()
                return file_path, "Image already valid"
            except (UnidentifiedImageError, IOError):
                try:
                    img = img.convert("RGB")
                    img.save(file_path)
                    return file_path, "Success"
                except Exception as e:
                    return file_path, f"Failed to save: {e}"

    def update_progress(self, processed_files, total_files):
        self.progress_bar["value"] = (processed_files / total_files) * 100
        self.status_label.config(text=self.get_text("Repairing files...").format(processed_files, total_files))

    def preview_images(self):
        # Placeholder for preview functionality, demonstrating how to implement a basic image preview.
        preview_window = tk.Toplevel(self)
        preview_window.title(self.get_text("Preview Window Title"))
        preview_window.geometry("800x600")
        images = [os.path.join(dp, f) for dp, dn, filenames in os.walk(self.selected_folder) for f in filenames if self.is_supported_format(f)]
        if images:
            img_path = images[0]  # Just show the first image as an example
            img = Image.open(img_path)
            img.thumbnail((800, 600))
            img = tk.PhotoImage(file=img_path)
            img_label = tk.Label(preview_window, image=img)
            img_label.image = img  # Keep a reference to avoid garbage collection
            img_label.pack()

if __name__ == "__main__":
    app = ImageRepairTool()
    app.mainloop()
