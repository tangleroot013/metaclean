# 🧹 metaclean

A lightweight, privacy-first Terminal User Interface (TUI) metadata scrubber.

`metaclean` is a completely local, offline tool that helps you inspect and safely remove hidden metadata (like GPS location, device details, and creation times) from your images, documents, and other files before you share them online.

## 🤔 What is Metadata, and Why Clean It?

When you take a picture with your phone, write a document, or record an audio file, your device secretly saves extra information inside that file. This is called **metadata** (or EXIF data for images).

This hidden information can include:

* **GPS Coordinates:** Exactly where you were when you took a photo (including your home or school address).

* **Device Specs:** The exact phone, camera, or computer model you used.

* **Software & Author Names:** The program used to edit the file and sometimes your real name.

* **Timestamps:** The exact second the file was created or modified.

Sharing files with this data online can accidentally share your private information. `metaclean` solves this by safely scrubbing that data away entirely on your own computer—**no data ever leaves your machine!**

## ✨ Features

* **💻 Beautiful TUI:** An easy-to-use keyboard-driven terminal interface. No complex command-line arguments to memorize!

* **🔒 Local & Secure:** 100% offline. Your files never get uploaded to any external server.

* **📁 Multi-Format Support:** Inspect and clean popular file formats (including PNG, JPEG, and PDF).

* **⚡ Safe Scrubbing:** Creates a clean copy of your files or cleans them in place with full user confirmation.

## 🚀 Getting Started

### Prerequisites

To run `metaclean`, you need **Python 3.8 or higher** installed on your computer.

### Installation

1. **Clone the repository:**

   ```
   git clone [https://github.com/tangleroot013/metaclean.git](https://github.com/tangleroot013/metaclean.git)
   cd metaclean
   ```

2. **Install dependencies:**
   *(Note: It is recommended to use a virtual environment)*

   ```
   pip install -r requirements.txt
   ```

   *(If you don't have a `requirements.txt` yet, `metaclean` typically uses standard Python libraries or simple libraries like `Pillow`. You can install it using `pip install Pillow`)*

## 🛠️ Usage

Simply run the Python script from your terminal:

```
python metaclean.py
```

### Navigating the TUI

* Use your **Arrow Keys** or **Tab** to navigate between options.

* Press **Space** or **Enter** to select a file or trigger a cleaning action.

* Follow the on-screen instructions to load a file, inspect its hidden metadata, and scrub it clean.

## 🤝 Contributing

We welcome contributions from developers of all skill levels! If you have suggestions to make `metaclean` better, feel free to:

1. Fork the project.

2. Create a feature branch (`git checkout -b feature/CoolNewFeature`).

3. Commit your changes (`git commit -m 'Add some cool feature'`).

4. Push to the branch (`git push origin feature/CoolNewFeature`).

5. Open a Pull Request.

## 📄 License

This project is open-source and licensed under the **MIT License**. Feel free to use, modify, and share it!
