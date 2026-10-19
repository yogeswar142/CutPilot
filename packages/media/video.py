"""
CutPilot Media Video Tools
Frame extraction and silent proxy generation for visual analysis pipelines.
"""
import subprocess
from pathlib import Path
from packages.core.config import settings

def extract_frame(video_path: str, timestamp_seconds: float, output_image_path: str) -> str:
    """
    Extracts a single high-quality frame from video at the given timestamp.
    """
    src = Path(video_path).resolve()
    dst = Path(output_image_path).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(settings.ffmpeg_path),
        "-y",
        "-ss", f"{timestamp_seconds:.3f}",
        "-i", str(src),
        "-vframes", "1",
        "-q:v", "2",
        str(dst)
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg frame extraction failed: {res.stderr}")

    return str(dst)

def create_silent_proxy(video_path: str, output_path: str) -> str:
    """
    Creates a video copy with the audio track stripped (for pure visual analysis).
    """
    src = Path(video_path).resolve()
    dst = Path(output_path).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(settings.ffmpeg_path),
        "-y",
        "-i", str(src),
        "-an",
        "-c:v", "copy",
        str(dst)
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg silent proxy creation failed: {res.stderr}")

    return str(dst)
