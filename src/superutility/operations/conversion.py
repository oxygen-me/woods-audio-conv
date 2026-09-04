from pathlib import Path
from models.operations import Remux, TranscodeVideo

def make_transcode(input_path: Path, output_path: Path, video_codec: str | None = None,
                   audio_codec: str | None = None) -> TranscodeVideo:
    return TranscodeVideo(
        operation_id="transcode-video",
        input_path=input_path,
        output_path=output_path,
        video_codec=video_codec,
        audio_codec=audio_codec,
    )

def make_remux(input_path: Path, output_path: Path) -> Remux:
    return Remux(
        operation_id="remux",
        input_path=input_path,
        output_path=output_path,
    )
