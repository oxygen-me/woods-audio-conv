from pathlib import Path
import subprocess
import tempfile

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

def ffmpeg_path():
    if imageio_ffmpeg is None:
        return None
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

def run_ffmpeg(args, cancel_check=None):
    exe = ffmpeg_path()
    if not exe:
        raise RuntimeError("Bundled FFmpeg is unavailable. Install imageio-ffmpeg.")
    p = subprocess.Popen(
        [exe, "-hide_banner", "-loglevel", "error", *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace")
    out, err = p.communicate()
    if cancel_check and cancel_check():
        try: p.kill()
        except Exception: pass
        raise InterruptedError("Cancelled")
    if p.returncode:
        raise RuntimeError(err.strip() or "FFmpeg failed.")
    return out

def unique_path(path: Path):
    if not path.exists():
        return path
    for n in range(1, 10000):
        p = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not p.exists():
            return p
    raise RuntimeError("Unable to create a unique output filename.")

def probe_media(path):
    exe = ffmpeg_path()
    if not exe:
        return {"type": "unknown", "raw": ""}
    p = subprocess.run(
        [exe, "-hide_banner", "-i", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    raw = (p.stderr or "") + "\n" + (p.stdout or "")
    low = raw.lower()
    kind = "video" if "video:" in low else ("audio" if "audio:" in low else "unknown")
    return {"type": kind, "raw": raw}

def ffmpeg_convert(src, dst, codec=None, bitrate=None, crf=None,
                   sample_rate=None, channels=None, video_codec=None,
                   fps=None, scale=None, extra=None, strip_metadata=False,
                   cancel_check=None):
    args = ["-y", "-i", str(src)]
    if strip_metadata:
        args += ["-map_metadata", "-1"]
    if video_codec:
        args += ["-c:v", video_codec]
    elif codec:
        args += ["-c:a", codec]
    if bitrate:
        args += ["-b:a", f"{bitrate}k"]
    if crf is not None:
        args += ["-crf", str(crf)]
    if sample_rate:
        args += ["-ar", str(sample_rate)]
    if channels:
        args += ["-ac", str(channels)]
    if fps:
        args += ["-r", str(fps)]
    if scale:
        args += ["-vf", f"scale={scale}"]
    if extra:
        args += list(extra)
    args += ["-map_metadata", "-1" if strip_metadata else "0", str(dst)]
    return run_ffmpeg(args, cancel_check)

def video_to_gif(src, dst, fps=12, width=720, cancel_check=None):
    with tempfile.TemporaryDirectory() as td:
        palette = Path(td) / "palette.png"
        run_ffmpeg(["-i", str(src), "-vf",
                    f"fps={fps},scale={width}:-1:flags=lanczos,palettegen",
                    str(palette)], cancel_check)
        run_ffmpeg(["-i", str(src), "-i", str(palette), "-lavfi",
                    f"fps={fps},scale={width}:-1:flags=lanczos[x];"
                    "[x][1:v]paletteuse=dither=sierra2_4a",
                    "-loop", "0", str(dst)], cancel_check)
