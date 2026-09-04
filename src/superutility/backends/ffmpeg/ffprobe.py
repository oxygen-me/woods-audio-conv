import json
import subprocess
from pathlib import Path

from app.paths import ffprobe_path
from models.media import MediaFile
from models.streams import Stream, VideoStream, AudioStream

class FFProbeBackend:
    def __init__(self, executable: Path | None = None):
        self.executable = executable or ffprobe_path()

    def probe(self, path: Path) -> MediaFile:
        if not self.executable.exists():
            raise FileNotFoundError(f"ffprobe.exe not found: {self.executable}")
        args = [
            str(self.executable), "-v", "error",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(path),
        ]
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "ffprobe failed")

        data = json.loads(completed.stdout)
        stat = path.stat()
        fmt = data.get("format", {})
        streams = tuple(self._stream(s) for s in data.get("streams", []))

        duration = _float(fmt.get("duration"))
        bitrate = _int(fmt.get("bit_rate"))

        return MediaFile(
            path=path,
            size=stat.st_size,
            format_name=fmt.get("format_name"),
            format_long_name=fmt.get("format_long_name"),
            duration=duration,
            bitrate=bitrate,
            streams=streams,
            metadata=dict(fmt.get("tags") or {}),
        )

    def _stream(self, raw: dict) -> Stream:
        common = dict(
            index=int(raw.get("index", -1)),
            kind=raw.get("codec_type", "unknown"),
            codec=raw.get("codec_name"),
            codec_id=raw.get("codec_tag_string"),
            profile=raw.get("profile"),
            bitrate=_int(raw.get("bit_rate")),
            duration=_float(raw.get("duration")),
            language=(raw.get("tags") or {}).get("language"),
            title=(raw.get("tags") or {}).get("title"),
            disposition=dict(raw.get("disposition") or {}),
        )
        if common["kind"] == "video":
            return VideoStream(
                **common,
                width=raw.get("width"),
                height=raw.get("height"),
                pixel_format=raw.get("pix_fmt"),
                fps=_fps(raw.get("avg_frame_rate")),
            )
        if common["kind"] == "audio":
            return AudioStream(
                **common,
                sample_rate=_int(raw.get("sample_rate")),
                channels=raw.get("channels"),
                channel_layout=raw.get("channel_layout"),
                sample_format=raw.get("sample_fmt"),
            )
        return Stream(**common)

def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _fps(value):
    if not value or value == "0/0":
        return None
    try:
        n, d = value.split("/", 1)
        return float(n) / float(d)
    except (ValueError, ZeroDivisionError):
        return None
