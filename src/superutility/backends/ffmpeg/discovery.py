from pathlib import Path
from ...app.paths import ffmpeg_path, ffprobe_path

def discover() -> dict[str, Path | None]:
    ffmpeg = ffmpeg_path()
    ffprobe = ffprobe_path()
    return {
        "ffmpeg": ffmpeg if ffmpeg.exists() else None,
        "ffprobe": ffprobe if ffprobe.exists() else None,
    }
