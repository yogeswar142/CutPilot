"""
CutPilot Media Package
FFmpeg / FFprobe media inspection, audio extraction, and frame capture.
"""
from packages.media.inspector import inspect_media
from packages.media.audio import extract_audio_16k_mono
from packages.media.video import extract_frame, create_silent_proxy

__all__ = [
    "inspect_media",
    "extract_audio_16k_mono",
    "extract_frame",
    "create_silent_proxy",
]
