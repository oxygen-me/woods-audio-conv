from pathlib import Path

from superutility.capabilities.evaluator import CapabilityEvaluator
from superutility.capabilities.model import CapabilityStatus
from superutility.models.media import MediaFile
from superutility.models.streams import VideoStream
from superutility.operations.conversion import make_transcode

def test_video_transcode_is_supported():
    media = MediaFile(
        path=Path("x.mp4"), size=1, format_name="mp4",
        format_long_name="MPEG-4", duration=1, bitrate=1,
        streams=(VideoStream(index=0, kind="video", codec="h264"),)
    )
    op = make_transcode(Path("x.mp4"), Path("x.out.mp4"))
    result = CapabilityEvaluator().evaluate(media, op)
    assert result.status == CapabilityStatus.SUPPORTED
