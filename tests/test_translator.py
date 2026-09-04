from pathlib import Path

from superutility.backends.ffmpeg.translator import FFmpegTranslator
from superutility.operations.conversion import make_remux

def test_translator_uses_argument_vector():
    operation = make_remux(Path(r"C:\Media\hello world.mp4"), Path(r"C:\Media\out.mkv"))
    args = FFmpegTranslator().translate(operation)
    assert args[0] == "-hide_banner"
    assert "hello world.mp4" in args
    assert "out.mkv" in args
    assert all(isinstance(x, str) for x in args)
