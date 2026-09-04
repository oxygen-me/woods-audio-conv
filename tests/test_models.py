from pathlib import Path

from superutility.models.media import MediaFile
from superutility.models.streams import VideoStream

def test_media_file_helpers():
    media = MediaFile(
        path=Path("hello world.mp4"),
        size=123,
        format_name="mov,mp4,m4a,3gp,3g2,mj2",
        format_long_name="QuickTime / MOV",
        duration=1.0,
        bitrate=1000,
        streams=(VideoStream(index=0, kind="video", codec="h264", width=1920, height=1080),),
    )
    assert media.filename == "hello world.mp4"
    assert len(media.video_streams) == 1
