# Image Repair Tool

A simple GUI tool to repair corrupted image files. Supports `.jpg`, `.jpeg`, `.png`, `.heif`, and `.heic`.

## Features

- **Folder Selection**: Choose a folder containing images to repair.
- **Multi-language Support**: Easily switch interface languages.
- **Progress Tracking**: Monitor repair progress.
- **Logging**: Detailed logs for each session.
- **Image Preview**: Basic preview of repaired images (upcoming feature).

## Installation

1. **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/image-repair-tool.git
    cd image-repair-tool
    ```

2. **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

## Usage

1. **Run the application:**
    ```bash
    python image_repair_tool.py
    ```

2. **Select a Folder**: Click "Select Folder" to choose your image directory.
3. **Start Repair**: Click "Start Repair" to begin fixing images.
4. **Preview Images**: Click "Preview Repaired Images" after repair (upcoming feature).

## Configuration

Update `language_texts.json` to add or modify languages.

## Logging

Logs are saved to `image_repair_tool.log`.

## Contributing

Fork the repository and submit a pull request with your improvements.

## License

This project is licensed under the MIT License.

---

Feel free to reach out with any questions or suggestions!
