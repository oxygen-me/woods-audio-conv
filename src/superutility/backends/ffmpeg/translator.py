from models.operations import Remux, TranscodeVideo, StreamMode

class FFmpegTranslator:
    def translate(self, operation) -> list[str]:
        args = ["-hide_banner", "-nostdin", "-y" if operation.overwrite else "-n"]

        if isinstance(operation, Remux):
            args += ["-i", str(operation.input_path), "-map", "0", "-c", "copy"]
            args += list(operation.extra_args)
            args += [str(operation.output_path)]
            return args

        if isinstance(operation, TranscodeVideo):
            args += ["-i", str(operation.input_path), "-map", "0"]
            if operation.stream_mode == StreamMode.COPY:
                args += ["-c", "copy"]
            else:
                if operation.video_codec:
                    args += ["-c:v", operation.video_codec]
                if operation.audio_codec:
                    args += ["-c:a", operation.audio_codec]
            args += list(operation.extra_args)
            args += [str(operation.output_path)]
            return args

        raise ValueError(f"Unsupported operation: {type(operation).__name__}")
