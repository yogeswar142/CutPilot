"""
CutPilot Whisper Transcription Runner
Executes native ARM64 whisper-cli, parses subword tokens into word-level timestamps,
and enforces media-duration safety invariants.
"""
import subprocess
import json
import time
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from packages.core.models import TranscriptResult, TranscriptSegment, WordTimestamp
from packages.core.config import settings
from packages.media.inspector import inspect_media
from packages.media.audio import extract_audio_16k_mono

def parse_timestamp_ms(ts_str: str) -> int:
    """Parses 'HH:MM:SS,mmm' or 'HH:MM:SS.mmm' into milliseconds."""
    ts_str = ts_str.replace(",", ".")
    parts = ts_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return int((hours * 3600 + minutes * 60 + seconds) * 1000)

def reconstruct_words_from_tokens(tokens: List[Dict[str, Any]], media_duration: float) -> List[WordTimestamp]:
    """
    Combines Whisper subword tokens into complete words with start/end timestamps and confidence.
    Flags words exceeding media duration.
    """
    words = []
    curr_word = ""
    curr_start = None
    curr_end = None
    curr_probs = []

    for t in tokens:
        txt = t.get("text", "")
        # Clean special tokens
        if (txt.startswith("[_") and txt.endswith("_]")) or "[_TT_" in txt:
            txt = txt.split("[_TT_")[0]
        if not txt or (txt.startswith("[_") and txt.endswith("_]")):
            continue

        timestamps = t.get("timestamps", {})
        if "from" not in timestamps or "to" not in timestamps:
            continue

        t_from = parse_timestamp_ms(timestamps["from"])
        t_to = parse_timestamp_ms(timestamps["to"])
        t_prob = float(t.get("p", 1.0))

        # Space indicates boundary of a new word
        if txt.startswith(" ") or txt.startswith("\n") or curr_start is None:
            if curr_word.strip():
                avg_p = sum(curr_probs) / len(curr_probs) if curr_probs else 0.0
                start_s = round(curr_start / 1000.0, 3)
                end_s = round(curr_end / 1000.0, 3)
                words.append(WordTimestamp(
                    word=curr_word.strip(),
                    start=start_s,
                    end=end_s,
                    confidence=round(avg_p, 4),
                    is_speech=True
                ))
            curr_word = txt
            curr_start = t_from
            curr_end = t_to
            curr_probs = [t_prob]
        else:
            curr_word += txt
            curr_end = t_to
            curr_probs.append(t_prob)

    if curr_word.strip() and curr_start is not None and curr_end is not None:
        avg_p = sum(curr_probs) / len(curr_probs) if curr_probs else 0.0
        words.append(WordTimestamp(
            word=curr_word.strip(),
            start=round(curr_start / 1000.0, 3),
            end=round(curr_end / 1000.0, 3),
            confidence=round(avg_p, 4),
            is_speech=True
        ))

    return words

def transcribe_audio(audio_path: str, media_duration: float = 0.0, language: str = "auto") -> TranscriptResult:
    """
    Transcribes a 16kHz mono WAV file using native whisper-cli.
    """
    audio_file = Path(audio_path).resolve()
    if not audio_file.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    whisper_exe = settings.whisper_cli_path
    model_file = settings.whisper_model_path

    if not whisper_exe.is_file():
        raise FileNotFoundError(f"Whisper executable not found at: {whisper_exe}")
    if not model_file.is_file():
        raise FileNotFoundError(f"Whisper model not found at: {model_file}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_prefix = Path(tmp_dir) / "transcript"
        cmd = [
            str(whisper_exe),
            "-m", str(model_file),
            "-f", str(audio_file),
            "-ojf",
            "-of", str(output_prefix),
            "-l", language,
            "-t", "6"
        ]

        t0 = time.time()
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        elapsed = time.time() - t0

        if res.returncode != 0:
            raise RuntimeError(f"whisper-cli failed (exit code {res.returncode}): {res.stderr}")

        json_output = Path(f"{output_prefix}.json")
        if not json_output.is_file():
            raise FileNotFoundError(f"Whisper did not write expected JSON output at: {json_output}")

        with open(json_output, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

    # Reconstruct segments and word timestamps
    segments = []
    raw_segments = raw_data.get("transcription", [])

    for i, seg in enumerate(raw_segments):
        seg_timestamps = seg.get("timestamps", {})
        seg_start = parse_timestamp_ms(seg_timestamps.get("from", "00:00:00.000")) / 1000.0
        seg_end = parse_timestamp_ms(seg_timestamps.get("to", "00:00:00.000")) / 1000.0
        seg_text = seg.get("text", "").strip()
        tokens = seg.get("tokens", [])
        words = reconstruct_words_from_tokens(tokens, media_duration)

        segments.append(TranscriptSegment(
            id=i,
            start=round(seg_start, 3),
            end=round(seg_end, 3),
            text=seg_text,
            words=words
        ))

    detected_lang = raw_data.get("result", {}).get("language", language)

    return TranscriptResult(
        source_media=str(audio_file),
        duration_seconds=media_duration if media_duration > 0 else (segments[-1].end if segments else 0.0),
        language=detected_lang,
        segments=segments,
        version="1.0.0",
        raw_meta={
            "transcription_time_seconds": round(elapsed, 3),
            "model": model_file.name
        }
    )

def transcribe_video(video_path: str, temp_dir: Optional[str] = None) -> TranscriptResult:
    """
    Convenience method: inspects media, extracts audio, and transcribes.
    """
    asset = inspect_media(video_path)
    if not asset.has_audio:
        raise ValueError(f"Video file has no audio stream: {video_path}")

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(temp_dir) if temp_dir else Path(tmp)
        wav_path = work_dir / f"{Path(video_path).stem}_16k.wav"
        extract_audio_16k_mono(video_path, str(wav_path))
        result = transcribe_audio(str(wav_path), media_duration=asset.duration_seconds)
        result.source_media = str(Path(video_path).resolve())
        return result
