import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageFile
import concurrent.futures
import threading
import filecmp

# Increase the maximum image file size limit
Image.MAX_IMAGE_PIXELS = None

class TextRedirector:
    def __init__(self, text_widget, tag):
        self.text_widget = text_widget
        self.tag = tag

    def write(self, str):
        self.text_widget.insert(tk.END, str, (self.tag,))
        self.text_widget.see(tk.END)

    def flush(self):
        pass

class ImageRepairTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image and Video Repair Tool")
        self.geometry("800x600")
        self.configure(bg="black")
        self.resizable(True, True)
        self.selected_folder = ""
        self.repairing = False

        self.create_widgets()

    def create_widgets(self):
        self.folder_label = tk.Label(self, text="", font=("Poppins", 14), bg="black", fg="white")
        self.folder_label.pack(pady=10)

        self.status_label = tk.Label(self, text="", font=("Poppins", 12), bg="black", fg="white")
        self.status_label.pack(pady=10)

        self.progress_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=600, mode="determinate", style="success.Horizontal.TProgressbar")
        self.progress_bar.pack(pady=20)

        self.log_text = tk.Text(self, height=10, width=80, wrap="word", bg="black", fg="white", font=("Poppins", 12))
        self.log_text.pack(pady=10)

        # Redirect stdout and stderr to the log text area
        sys.stdout = TextRedirector(self.log_text, "stdout")
        sys.stderr = TextRedirector(self.log_text, "stderr")

        self.select_folder_button = tk.Button(self, text="Select Folder", command=self.select_folder, bg="#007acc", fg="white", font=("Poppins", 14))
        self.select_folder_button.pack(pady=10)

        self.start_button = tk.Button(self, text="Start Repair", command=self.start_repair, bg="#007acc", fg="white", font=("Poppins", 14), state=tk.DISABLED)
        self.start_button.pack(pady=10)

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
        threading.Thread(target=self.scan_folder).start()

    def scan_folder(self):
        self.progress_bar["value"] = 0
        self.status_label.config(text="Scanning files...")
        self.log_text.delete(1.0, tk.END)

        total_files = sum(len(files) for _, _, files in os.walk(self.selected_folder))
        processed_files = 0
        repaired_files = 0
        corrupted_files = 0

        processed_files_set = set()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for root, _, files in os.walk(self.selected_folder):
                for file in files:
                    file_path = os.path.normpath(os.path.join(root, file))
                    if file_path in processed_files_set:
                        continue

                    if self.is_supported_format(file_path):
                        futures.append(executor.submit(self.repair_file, file_path))
                        processed_files_set.add(file_path)
                        processed_files += 1
                        self.update_progress(processed_files, total_files)

            for future in concurrent.futures.as_completed(futures):
                if self.repairing:
                    try:
                        result = future.result()
                        if result[1] == "Success":
                            repaired_files += 1
                        else:
                            corrupted_files += 1
                            error_message = f"Error repairing file '{result[0]}': {result[1]}"
                            self.log_text.insert(tk.END, error_message + "\n")
                    except Exception as e:
                        self.log_text.insert(tk.END, f"Error: {e}\n")
                        corrupted_files += 1

        self.progress_bar["value"] = 100
        self.status_label.config(
            text=f"Repair complete. Repaired {repaired_files} out of {processed_files} files. {corrupted_files} files could not be repaired.")
        self.log_text.see(tk.END)
        self.repairing = False

        self.delete_duplicates()

    def is_supported_format(self, file_path):
        _, ext = os.path.splitext(file_path)
        supported_formats = [".jpg", ".jpeg", ".png", ".heif", ".heic"]
        return ext.lower() in supported_formats

    def repair_file(self, file_path):
        try:
            with Image.open(file_path) as img:
                img = img.copy()

                if not img.verify():
                    img = img.convert("RGB")
                    img.save(file_path)
                    return file_path, "Success"
                else:
                    try:
                        img = Image.open(file_path)
                        img.verify()
                        return file_path, "Image already valid"
                    except Exception as e:
                        try:
                            img = Image.open(file_path)
                            img.load()
                            return file_path, "Image may be partially corrupt"
                        except Exception as e:
                            return file_path, f"Image is corrupt: {e}"

        except FileNotFoundError:
            return file_path, "File not found"
        except PermissionError:
            return file_path, "Permission denied"
        except IsADirectoryError:
            return file_path, "Is a directory"
        except Exception as e:
            return file_path, f"Error: {e}"

    def update_progress(self, processed_files, total_files):
        self.progress_bar["value"] = (processed_files / total_files) * 100
        self.status_label.config(text=f"Repairing files... ({processed_files}/{total_files})")

    def delete_duplicates(self):
        duplicates = []
        for root, _, files in os.walk(self.selected_folder):
            for file in files:
                file_path = os.path.normpath(os.path.join(root, file))
                if file_path in duplicates:
                    continue
                for other_file in files:
                    if file != other_file:
                        other_file_path = os.path.normpath(os.path.join(root, other_file))
                        if filecmp.cmp(file_path, other_file_path, shallow=False):
                            duplicates.append(other_file_path)
                            break

        if duplicates:
            confirm = messagebox.askyesno("Delete Duplicates", f"Do you want to delete {len(duplicates)} duplicate files?")
            if confirm:
                for duplicate in duplicates:
                    try:
                        os.remove(duplicate)
                        self.log_text.insert(tk.END, f"Deleted duplicate file: {duplicate}\n")
                    except Exception as e:
                        self.log_text.insert(tk.END, f"Error deleting duplicate file '{duplicate}': {e}\n")

                self.log_text.insert(tk.END, f"Deleted {len(duplicates)} duplicate files.\n")
            else:
                self.log_text.insert(tk.END, "Duplicate file deletion cancelled by user.\n")
        else:
            self.log_text.insert(tk.END, "No duplicate files found.\n")
        self.log_text.see(tk.END)
        self.progress_bar['value'] = 0

if __name__ == "__main__":
    app = ImageRepairTool()
    app.mainloop()
