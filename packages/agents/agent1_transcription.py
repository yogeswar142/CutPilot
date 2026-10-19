"""
CutPilot Agent 1 — Transcription & Speech Timing
Coordinates audio extraction, native ARM64 Whisper speech recognition, and duration validation.
"""
from typing import Dict, Any, Tuple, List
from packages.core.models import TranscriptResult
from packages.core.validation import validate_transcript_bounds
from packages.transcription.whisper_runner import transcribe_video
from packages.media.inspector import inspect_media

def run_agent1_transcription(video_path: str) -> Tuple[TranscriptResult, List[str]]:
    """
    Executes Agent 1 workflow:
    1. Inspects media container duration and audio streams.
    2. Runs native Whisper.cpp transcription.
    3. Validates that no timestamp exceeds media duration.
    """
    asset = inspect_media(video_path)
    transcript = transcribe_video(video_path)

    # Validate against actual asset duration
    is_valid, issues = validate_transcript_bounds(transcript, asset.duration_seconds)
    return transcript, issues
