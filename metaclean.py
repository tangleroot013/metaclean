#!/usr/bin/env python3
"""metaclean.py — TUI metadata cleaner: auto-detect, clean, idempotent, privacy-first."""
import curses
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

OUTPUT_DIR = Path.home() / "MetaCleaned"
MANIFEST = OUTPUT_DIR / ".manifest.json"
SUPPORTED = {
    ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp",
    ".pdf", ".docx", ".xlsx", ".pptx",
    ".mp3", ".flac", ".m4a", ".ogg", ".wma",
    ".mp4", ".mov", ".avi", ".mkv",
}
SCAN_DIRS = [
    Path.home() / "Downloads",
    Path.home() / "Desktop",
    Path.home() / "Pictures",
    Path.home() / "Documents",
    Path.home() / "Screenshots",
]

class Colors:
    OKBLUE = "\033[94m"; OKCYAN = "\033[96m"; OKGREEN = "\033[92m"
    WARNING = "\033[93m"; FAIL = "\033[91m"; ENDC = "\033[0m"; BOLD = "\033[1m"

def load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text())
        except json.JSONDecodeError:
            return {}
    return {}

def save_manifest(m: dict):
    OUTPUT_DIR.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2))

def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def find_last_media() -> Optional[Path]:
    candidates = []
    for d in SCAN_DIRS:
        if not d.is_dir():
            continue
        for root, _, files in os.walk(d):
            if OUTPUT_DIR.name in root or "/." in root:
                continue
            for f in files:
                p = Path(root) / f
                if p.suffix.lower() in SUPPORTED:
                    try:
                        candidates.append((p.stat().st_mtime, p))
                    except OSError:
                        continue
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]

def human_ago(mtime: float) -> str:
    delta = datetime.now().timestamp() - mtime
    if delta < 60: return f"{int(delta)}s ago"
    if delta < 3600: return f"{int(delta / 60)}m ago"
    if delta < 86400: return f"{int(delta / 3600)}h ago"
    return f"{int(delta / 86400)}d ago"

def browse(stdscr):
    curses.curs_set(0)
    curses.use_default_colors()
    cwd = Path.home()
    idx = 0
    latest_media = find_last_media()
    while True:
        try:
            entries = sorted(
                [".."] + [e.name for e in cwd.iterdir()],
                key=lambda x: (not (cwd / x).is_dir() if x != ".." else False, x.lower()),
            )
        except PermissionError:
            entries = [".."]
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        stdscr.addstr(0, 0, f"metaclean :: {cwd}"[: w - 1], curses.A_BOLD)
        stdscr.addstr(1, 0, "up/down move  ENTER select  BACKSPACE up  L quick-load  q quit"[: w - 1])
        offset = 3
        if latest_media:
            shortcut = f"[L] Quick load: {latest_media.name} (from {latest_media.parent.name})"
            try:
                stdscr.addstr(2, 0, shortcut[: w - 1], curses.A_STANDOUT)
            except curses.error:
                pass
            offset = 4
        for i, name in enumerate(entries[: h - offset - 1]):
            full = cwd / name if name != ".." else cwd.parent
            tag = "/" if name != ".." and full.is_dir() else ""
            attr = curses.A_REVERSE if i == idx else curses.A_NORMAL
            try:
                stdscr.addstr(i + offset, 2, f"{name}{tag}"[: w - 3], attr)
            except curses.error:
                pass
        stdscr.refresh()
        key = stdscr.getch()
        if key == curses.KEY_UP and idx > 0:
            idx -= 1
        elif key == curses.KEY_DOWN and idx < len(entries[: h - offset - 1]) - 1:
            idx += 1
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            cwd = cwd.parent; idx = 0
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

def pick_file() -> Optional[Path]:
    try:
        return curses.wrapper(browse)
    except Exception:
        print(f"\n{Colors.WARNING}Curses unavailable. Falling back to path input.{Colors.ENDC}")
        raw = input("Enter full file path: ").strip()
        p = Path(raw).expanduser()
        return p if p.exists() else None

def clean_jpeg(data: bytes):
    if data[:2] != b"\xff\xd8":
        return data, []
    removed = []
    seg_names = {0xE1: "EXIF", 0xE2: "ICC/FlashPix", 0xED: "IPTC/Photoshop", 0xEE: "Adobe"}
    out = bytearray(data[:2]); i = 2
    while i < len(data) - 1:
        if data[i] != 0xFF:
            out += data[i:]; break
        marker = data[i + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            out += data[i:i + 2]; i += 2; continue
        if marker == 0xDA:
            out += data[i:]; break
        seg_len = int.from_bytes(data[i + 2:i + 4], "big")
        if marker in seg_names:
            removed.append(seg_names[marker]); i += 2 + seg_len; continue
        out += data[i:i + 2 + seg_len]; i += 2 + seg_len
    return bytes(out), removed

def clean_png(data: bytes):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return data, []
    strip = {b"tEXt", b"zTXt", b"iTXt", b"tIME", b"eXIf"}
    removed = []; out = bytearray(data[:8]); i = 8
    while i < len(data):
        length = int.from_bytes(data[i:i + 4], "big")
        ctype = data[i + 4:i + 8]
        total = 12 + length
        if ctype in strip:
            removed.append(ctype.decode())
        else:
            out += data[i:i + total]
        i += total
        if ctype == b"IEND":
            break
    return bytes(out), removed

def clean_image_pillow(src: Path, dst: Path):
    try:
        from PIL import Image
    except ImportError:
        shutil.copy2(src, dst)
        return ["NOT CLEANED — copied as-is (pip install Pillow to strip metadata)"]
    img = Image.open(src)
    fresh = Image.new(img.mode, img.size)
    fresh.putdata(list(img.getdata()))
    fresh.save(dst, format=img.format)
    return ["all EXIF/XMP/ICC metadata (Pillow re-encode)"]

def clean_office(src: Path, dst: Path):
    strip_names = {"docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"}
    removed = []
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename in strip_names:
                removed.append(item.filename); continue
            zout.writestr(item, zin.read(item.filename))
    return removed

def clean_pdf(data: bytes):
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return None, None
    reader = PdfReader(io.BytesIO(data))
    fields = list((reader.metadata or {}).keys())
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({})
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue(), fields

def clean_audio(src: Path, dst: Path):
    try:
        from mutagen import File as MutagenFile
    except ImportError:
        shutil.copy2(src, dst)
        return ["NOT CLEANED — copied as-is (pip install mutagen to strip tags)"]
    shutil.copy2(src, dst)
    audio = MutagenFile(dst)
    if audio and audio.tags:
        fields = list(audio.tags.keys())
        audio.delete()
        audio.save()
        return fields
    return ["no tags found"]

def clean_video(src: Path, dst: Path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        shutil.copy2(src, dst)
        return ["NOT CLEANED — copied as-is (install ffmpeg to strip metadata)"]
    cmd = [ffmpeg, "-i", str(src), "-map_metadata", "-1",
           "-c:v", "copy", "-c:a", "copy", "-y", str(dst)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode == 0:
        return ["all container/stream metadata (ffmpeg -map_metadata -1)"]
    shutil.copy2(src, dst)
    return [f"NOT CLEANED — ffmpeg failed, copied as-is (exit {result.returncode})"]

def deterministic_dest(stem: str, ext: str, src_hash: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR / f"{stem}_clean_{src_hash[:8]}{ext}"

def confirm(prompt: str) -> bool:
    return input(f"{prompt} [Y/n] ").strip().lower() in ("", "y", "yes")

def open_folder(path: Path):
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif sys.platform == "win32":
            subprocess.run(["explorer", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except FileNotFoundError:
        print(f"{Colors.WARNING}No file-manager opener found for this platform.{Colors.ENDC}")

def main():
    print(f"{Colors.OKCYAN}{Colors.BOLD}")
    print("============================================================")
    print("   metaclean — privacy-first metadata scrubber")
    print("   local-only . hash-keyed . idempotent . no network")
    print("============================================================")
    print(Colors.ENDC)
    last = find_last_media()
    path = None
    if last:
        print(f"{Colors.OKGREEN}Last saved media:{Colors.ENDC} {last}  ({human_ago(last.stat().st_mtime)})")
        if confirm("Use this file?"):
            path = last
    if path is None:
        print(f"\n{Colors.OKBLUE}Opening file browser (press L any time to quick-load the same file)...{Colors.ENDC}")
        path = pick_file()
    if not path:
        print(f"{Colors.WARNING}cancelled.{Colors.ENDC}")
        return
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        print(f"{Colors.FAIL}Unsupported type: {ext}{Colors.ENDC}")
        return
    raw = path.read_bytes()
    src_hash = sha256_of(raw)
    manifest = load_manifest()
    if src_hash in manifest:
        entry = manifest[src_hash]
        out_path = Path(entry["output"])
        print(f"\n{Colors.WARNING}Already cleaned on {entry['cleaned_at']}.{Colors.ENDC}")
        print(f"Existing copy: {out_path}")
        print("No action taken (idempotent). Delete the manifest entry to force a reclean.")
        return
    dst = deterministic_dest(path.stem, ext, src_hash)
    removed_fields = []
    if ext in (".jpg", ".jpeg"):
        cleaned, removed_fields = clean_jpeg(raw); dst.write_bytes(cleaned)
    elif ext == ".png":
        cleaned, removed_fields = clean_png(raw); dst.write_bytes(cleaned)
    elif ext in (".tiff", ".tif", ".bmp", ".gif", ".webp"):
        removed_fields = clean_image_pillow(path, dst)
    elif ext in (".docx", ".xlsx", ".pptx"):
        removed_fields = clean_office(path, dst)
    elif ext == ".pdf":
        cleaned, removed_fields = clean_pdf(raw)
        if cleaned is None:
            print(f"{Colors.FAIL}pypdf not installed — run: pip install pypdf{Colors.ENDC}")
            return
        dst.write_bytes(cleaned)
    elif ext in (".mp3", ".flac", ".m4a", ".ogg", ".wma"):
        removed_fields = clean_audio(path, dst)
    elif ext in (".mp4", ".mov", ".avi", ".mkv"):
        removed_fields = clean_video(path, dst)
    out_hash = sha256_of(dst.read_bytes())
    manifest[src_hash] = {
        "output": str(dst),
        "output_sha256": out_hash,
        "cleaned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fields_removed": removed_fields,
    }
    save_manifest(manifest)
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- metaclean report ---{Colors.ENDC}")
    print(f"  source size:    {len(raw):,} bytes")
    print(f"  output size:    {dst.stat().st_size:,} bytes")
    print(f"  fields removed: {removed_fields if removed_fields else 'none found (already clean)'}")
    print(f"  saved to:       {Colors.OKCYAN}{dst}{Colors.ENDC}")
    print(f"\n  {Colors.OKGREEN}Source file left untouched.{Colors.ENDC}")
    print(f"  Manifest: {MANIFEST}")
    if confirm(f"\nOpen {OUTPUT_DIR}?"):
        open_folder(OUTPUT_DIR)

if __name__ == "__main__":
    main()
