"""Safe local FFmpeg helpers for media conversion and voice cleanup."""
from pathlib import Path
import shutil
import subprocess


class MediaToolError(RuntimeError):
    pass


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise MediaToolError("FFmpeg is not installed or not on PATH")
    return path


def _run(args: list[str], timeout_seconds: int = 900) -> Path:
    try:
        subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        raise MediaToolError("FFmpeg operation timed out") from exc
    except subprocess.CalledProcessError as exc:
        # Do not expose arbitrary input metadata or full command output in API errors.
        raise MediaToolError("FFmpeg failed; inspect protected server logs") from exc
    return Path(args[-1])


def extract_audio(source: str, output: str) -> Path:
    src, dst = Path(source), Path(output)
    if not src.is_file():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    return _run([_ffmpeg(), "-nostdin", "-y", "-i", str(src), "-vn", "-ac", "2",
                 "-ar", "48000", str(dst)])


def normalize_voice(source: str, output: str, *, denoise: bool = True) -> Path:
    """Normalize loudness and optionally apply FFmpeg's afftdn filter."""
    src, dst = Path(source), Path(output)
    if not src.is_file():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    filters = []
    if denoise:
        filters.append("afftdn=nf=-25")
    filters.extend(["highpass=f=75", "lowpass=f=16000", "loudnorm=I=-16:TP=-1.5:LRA=11"])
    return _run([_ffmpeg(), "-nostdin", "-y", "-i", str(src), "-af", ",".join(filters),
                 "-c:a", "aac", "-b:a", "192k", str(dst)])


def transcode_video(source: str, output: str, *, max_width: int = 1920) -> Path:
    if max_width < 320 or max_width > 3840:
        raise ValueError("max_width must be between 320 and 3840")
    src, dst = Path(source), Path(output)
    if not src.is_file():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale='min({max_width},iw)':-2"
    return _run([_ffmpeg(), "-nostdin", "-y", "-i", str(src), "-vf", vf,
                 "-c:v", "libx264", "-preset", "medium", "-crf", "22",
                 "-c:a", "aac", "-movflags", "+faststart", str(dst)])
