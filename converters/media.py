from pathlib import Path
from core.engine import ffmpeg_convert, video_to_gif, unique_path

AUDIO_FORMATS = {
    "MP3": (".mp3", "libmp3lame"),
    "WAV": (".wav", "pcm_s16le"),
    "FLAC": (".flac", "flac"),
    "OGG": (".ogg", "libvorbis"),
    "Opus": (".opus", "libopus"),
    "AAC / M4A": (".m4a", "aac"),
    "AIFF": (".aiff", "pcm_s16be"),
}
VIDEO_FORMATS = {
    "MP4": (".mp4", "libx264"),
    "MKV": (".mkv", "libx264"),
    "WebM": (".webm", "libvpx-vp9"),
    "MOV": (".mov", "libx264"),
    "AVI": (".avi", "mpeg4"),
}

def convert_audio(src, out_dir, fmt, bitrate, cancel_check=None):
    ext, codec = AUDIO_FORMATS[fmt]
    dst = unique_path(Path(out_dir) / (Path(src).stem + ext))
    ffmpeg_convert(src, dst, codec=codec, bitrate=bitrate, cancel_check=cancel_check)
    return dst

def convert_video(src, out_dir, fmt, crf=23, cancel_check=None):
    ext, codec = VIDEO_FORMATS[fmt]
    dst = unique_path(Path(out_dir) / (Path(src).stem + ext))
    extra = ["-movflags", "+faststart"] if fmt == "MP4" else None
    ffmpeg_convert(src, dst, video_codec=codec, crf=crf,
                   extra=extra, cancel_check=cancel_check)
    return dst

def extract_audio(src, out_dir, fmt, bitrate, cancel_check=None):
    return convert_audio(src, out_dir, fmt, bitrate, cancel_check)

def to_gif(src, out_dir, fps=12, width=720, cancel_check=None):
    dst = unique_path(Path(out_dir) / (Path(src).stem + ".gif"))
    video_to_gif(src, dst, fps, width, cancel_check)
    return dst
