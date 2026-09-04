import subprocess
from dataclasses import dataclass
from typing import Callable, Sequence

@dataclass(frozen=True, slots=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str

class ProcessRunner:
    def run(self, args: Sequence[str], on_stderr: Callable[[str], None] | None = None) -> ProcessResult:
        process = subprocess.Popen(
            list(args),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout, stderr = process.communicate()
        if on_stderr and stderr:
            on_stderr(stderr)
        return ProcessResult(process.returncode, stdout, stderr)
