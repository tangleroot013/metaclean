# metaclean

A lightweight, privacy-first terminal metadata scrubber.

`metaclean` is a completely local, offline tool that removes hidden metadata
(GPS location, device details, author names, timestamps) from images,
documents, audio, and video before you share them.

## Why

Photos, documents, and media files carry hidden metadata your device writes
automatically: GPS coordinates, device model, editing software, author name,
exact creation timestamp. Sharing a file with this intact can leak your
location or identity without you realizing it. metaclean strips it — nothing
ever leaves your machine.

## Features

- Auto-detects your most recently saved media file across common folders
  (Downloads, Desktop, Pictures, Documents, Screenshots) and offers to load
  it directly, or press `L` inside the file browser to quick-load it anytime
- Idempotent: a SHA-256 manifest tracks what's already been cleaned, so
  re-running on the same file is a no-op instead of creating duplicates
- Privacy-first: manifest stores only hashes and output paths, never source
  file paths or content; zero network calls
- Zero-dependency cleaning for JPEG, PNG, and Office formats (docx/xlsx/pptx)
  via raw binary/zip parsing — no libraries required
- Optional extended support: TIFF/BMP/GIF/WebP (Pillow), PDF (pypdf),
  audio tags (mutagen), video containers (ffmpeg) — each degrades honestly
  and tells you exactly what wasn't cleaned if the dependency is missing
- Curses TUI file browser as a fallback to the auto-detect prompt

## Requirements

Python 3.8+. Everything else is optional:

pip install Pillow pypdf mutagen --break-system-packages

(video cleaning also needs ffmpeg installed as a system package)

## Usage

python3 metaclean.py

You'll be offered your most recently saved media file first. Say no (or none
is found) and a keyboard-driven file browser opens — arrow keys to navigate,
Enter to select, L to quick-load the detected file, q to quit.

Cleaned copies are saved to ~/MetaCleaned/, named <original>_clean_<hash>.ext.
Your original file is never modified or moved.

## License

MIT
