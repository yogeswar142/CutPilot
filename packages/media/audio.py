"""
CutPilot Media Audio Extraction
Converts source video/audio into 16kHz mono WAV for Whisper.cpp.
"""
import subprocess
from pathlib import Path
from packages.core.config import settings

def extract_audio_16k_mono(input_path: str, output_wav_path: str) -> str:
    """
    Extracts 16kHz 16-bit mono PCM audio from input media using native FFmpeg.
    """
    src = Path(input_path).resolve()
    dst = Path(output_wav_path).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not src.is_file():
        raise FileNotFoundError(f"Source file not found: {src}")

    cmd = [
        str(settings.ffmpeg_path),
        "-y",
        "-i", str(src),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(dst)
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr}")

    return str(dst)
