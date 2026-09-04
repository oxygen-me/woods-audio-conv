from .ffmpeg.backend import FFmpegBackend

class BackendRegistry:
    def __init__(self):
        self.ffmpeg = FFmpegBackend()
