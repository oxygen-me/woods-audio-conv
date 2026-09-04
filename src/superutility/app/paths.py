from pathlib import Path
import sys

APP_NAME = "Multimedia Superutility"

def project_root() -> Path:
    # Development-friendly. Packaged builds can replace this policy later.
    return Path(__file__).resolve().parents[3]

def runtime_dir() -> Path:
    return project_root() / "runtime"

def ffmpeg_path() -> Path:
    return runtime_dir() / "ffmpeg.exe"

def ffprobe_path() -> Path:
    return runtime_dir() / "ffprobe.exe"

def data_dir() -> Path:
    base = Path.home() / "AppData" / "Local" / "MultimediaSuperutility"
    base.mkdir(parents=True, exist_ok=True)
    return base

def history_db_path() -> Path:
    return data_dir() / "history.sqlite3"
