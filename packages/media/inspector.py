"""
CutPilot Media Inspector
Extracts technical metadata, frame rates, and stream specs using native FFprobe.
"""
import subprocess
import json
from pathlib import Path
from typing import Optional
from packages.core.models import MediaAsset
from packages.core.config import settings

def parse_fps(r_frame_rate: str) -> float:
    """Parses fractions like '30/1' or '24000/1001' into float."""
    if not r_frame_rate:
        return 24.0
    if "/" in r_frame_rate:
        num, den = r_frame_rate.split("/")
        den_f = float(den)
        return float(num) / den_f if den_f != 0 else 24.0
    return float(r_frame_rate)

def inspect_media(file_path: str) -> MediaAsset:
    """
    Inspects a media file using ffprobe and returns a typed MediaAsset contract.
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Media file not found: {path}")

    cmd = [
        str(settings.ffprobe_path),
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-print_format", "json",
        str(path)
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    probe = json.loads(res.stdout)

    streams = probe.get("streams", [])
    format_info = probe.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = float(format_info.get("duration", 0.0))
    file_size = int(format_info.get("size", path.stat().st_size))

    fps = 24.0
    width = 0
    height = 0
    total_frames = None

    if video_stream:
        fps = parse_fps(video_stream.get("r_frame_rate", "24/1"))
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        nb_frames = video_stream.get("nb_frames")
        if nb_frames and nb_frames.isdigit():
            total_frames = int(nb_frames)
        elif duration > 0 and fps > 0:
            total_frames = int(round(duration * fps))

    sample_rate = int(audio_stream.get("sample_rate")) if audio_stream and audio_stream.get("sample_rate") else None
    channels = int(audio_stream.get("channels")) if audio_stream and audio_stream.get("channels") else None

    return MediaAsset(
        file_path=str(path),
        file_name=path.name,
        file_size_bytes=file_size,
        duration_seconds=duration,
        fps=fps,
        width=width,
        height=height,
        has_video=video_stream is not None,
        has_audio=audio_stream is not None,
        audio_sample_rate=sample_rate,
        audio_channels=channels,
        total_frames=total_frames
    )
