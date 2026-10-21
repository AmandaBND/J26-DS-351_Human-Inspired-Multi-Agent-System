
import shutil
import subprocess
from pathlib import Path


class AudioConversionService:
    """Convert phone recordings into 16 kHz mono WAV audio."""

    SUPPORTED_EXTENSIONS = {
        ".wav", ".mp3", ".m4a", ".amr", ".3gp", ".mp4"
    }

    def __init__(self, ffmpeg_path=None):
        # Use FFmpeg from PATH when available.
        # Otherwise, use the verified local Windows installation.
        self.ffmpeg_path = (
            ffmpeg_path
            or shutil.which("ffmpeg")
            or r"C:\ffmeg\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe"
        )

    def convert_to_wav(self, input_path, output_path):
        source = Path(input_path)
        destination = Path(output_path)

        if not source.is_file():
            raise FileNotFoundError(
                f"Audio recording not found: {source}"
            )

        if source.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported audio format: {source.suffix}"
            )

        if source.resolve() == destination.resolve():
            raise ValueError(
                "Input and output paths cannot be the same."
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        command = [
            self.ffmpeg_path,
            "-nostdin",
            "-y",
            "-i", str(source),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "pcm_s16le",
            str(destination)
        ]

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=120
            )

        except FileNotFoundError as exc:
            raise RuntimeError(
                "FFmpeg executable was not found."
            ) from exc

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "Audio conversion exceeded the time limit."
            ) from exc

        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"Audio conversion failed: {exc.stderr[-500:]}"
            ) from exc

        return str(destination)
