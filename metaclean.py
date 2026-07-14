#!/usr/bin/env python3
"""metaclean.py — TUI metadata cleaner: walk, select, clean, resave."""
import curses
import os
import glob
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path.home() / "MetaCleaned"

# ---------- auto-media finder logic ----------
def get_latest_media_file() -> Path or None:
    """
    Scans standard directories (Downloads, Pictures, Desktop)
    and returns the Path object of the most recently saved media file.
    """
    extensions = {'*.jpg', '*.jpeg', '*.png', '*.gif', '*.mp4', '*.mov', '*.pdf'}
    home_dir = Path.home()
    
    folders_to_check = [
        home_dir / 'Downloads',
        home_dir / 'Pictures',
        home_dir / 'Desktop'
    ]
    
    all_media_files = []
    
    for folder in folders_to_check:
        if not folder.exists():
            continue
            
        for ext in extensions:
            all_media_files.extend(folder.glob(ext))
            all_media_files.extend(folder.glob(ext.upper()))
            
    if not all_media_files:
        return None
        
    return max(all_media_files, key=os.path.getmtime)

# ---------- curses file browser ----------
def browse(stdscr):
    curses.curs_set(0)
    curses.use_default_colors()
    cwd = Path.home()
    idx = 0
    
    latest_media = get_latest_media_file()
    
    while True:
        entries = sorted(
            [".."] + [e.name for e in cwd.iterdir()],
            key=lambda x: (not (cwd / x).is_dir() if x != ".." else False, x.lower()),
        )
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        
        stdscr.addstr(0, 0, f"metaclean :: {cwd}"[: w - 1], curses.A_BOLD)
        stdscr.addstr(1, 0, "up/down move  ENTER open/select  BACKSPACE up  q quit"[: w - 1])
        
        offset = 3
        if latest_media:
            shortcut_text = f"✨ [L] Quick Load Latest Media: {latest_media.name} (from {latest_media.parent.name})"
            stdscr.addstr(2, 0, shortcut_text[: w - 1], curses.A_STANDOUT)
            offset = 4
            
        for i, name in enumerate(entries[: h - offset - 1]):
            full = cwd / name if name != ".." else cwd.parent
            tag = "/" if name != ".." and full.is_dir() else ""
            attr = curses.A_REVERSE if i == idx else curses.A_NORMAL
            stdscr.addstr(i + offset, 2, f"{name}{tag}"[: w - 3], attr)
            
        stdscr.refresh()
        key = stdscr.getch()
        
        if key == curses.KEY_UP and idx > 0:
            idx -= 1
        elif key == curses.KEY_DOWN and idx < len(entries[: h - offset - 1]) - 1:
            idx += 1
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            cwd = cwd.parent
            idx = 0
        elif key in (ord("l"), ord("L")) and latest_media:
            return latest_media
        elif key in (ord("q"), 27):
            return None
        elif key in (10, 13, curses.KEY_ENTER):
            sel = entries[idx]
            target = cwd.parent if sel == ".." else cwd / sel
            if target.is_dir():
                cwd, idx = target, 0
            else:
                return target

def pick_file():
    return curses.wrapper(browse)

# ---------- cleaners ----------
def clean_jpeg(data: bytes) -> bytes:
    if data[:2] != b"\xff\xd8":
        return data
    out = bytearray(data[:2])
    i = 2
    while i < len(data) - 1:
        if data[i] != 0xFF:
            out += data[i:]
            break
        marker = data[i + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            out += data[i:i + 2]
            i += 2
            continue
        if marker == 0xDA:
            out += data[i:]
            break
        seg_len = int.from_bytes(data[i + 2:i + 4], "big")
        if marker in (0xE1, 0xE2, 0xED, 0xEE):
            i += 2 + seg_len
            continue
        out += data[i:i + 2 + seg_len]
        i += 2 + seg_len
    return bytes(out)

def clean_png(data: bytes) -> bytes:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return data
    strip = {b"tEXt", b"zTXt", b"iTXt", b"tIME", b"eXIf"}
    out = bytearray(data[:8])
    i = 8
    while i < len(data):
        length = int.from_bytes(data[i:i + 4], "big")
        ctype = data[i + 4:i + 8]
        total = 12 + length
        if ctype not in strip:
            out += data[i:i + total]
        i += total
        if ctype == b"IEND":
            break
    return bytes(out)

def clean_office(src: Path, dst: Path):
    strip_names = {"docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"}
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename in strip_names:
                continue
            zout.writestr(item, zin.read(item.filename))

def clean_pdf(data: bytes):
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return None
    import io
    reader = PdfReader(io.BytesIO(data))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({})
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

# ---------- driver ----------
def unique_dest(name: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    dst = OUTPUT_DIR / name
    if not dst.exists():
        return dst
    stem, ext = os.path.splitext(name)
    return OUTPUT_DIR / f"{stem}_{datetime.now():%Y%m%d%H%M%S}{ext}"

def main():
    print("metaclean :: select a file to scrub metadata from\n")
    path = pick_file()
    if not path:
        print("cancelled.")
        return
    print(f"selected: {path}")
    ext = path.suffix.lower()
    dst = unique_dest(path.name)

    if ext in (".jpg", ".jpeg"):
        dst.write_bytes(clean_jpeg(path.read_bytes()))
    elif ext == ".png":
        dst.write_bytes(clean_png(path.read_bytes()))
    elif ext in (".docx", ".xlsx", ".pptx"):
        clean_office(path, dst)
    elif ext == ".pdf":
        cleaned = clean_pdf(path.read_bytes())
        if cleaned is None:
            print("pypdf not installed — run: pip install pypdf")
            return
        dst.write_bytes(cleaned)
    else:
        print(f"unsupported type: {ext} — copying as-is")
        shutil.copy2(path, dst)

    print(f"cleaned copy saved to: {dst}")

if __name__ == "__main__":
    main()
