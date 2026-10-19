"""
CutPilot Captions Generator
Generates synchronized .srt and .vtt caption files from Agent 1 word-level transcripts.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Union
from packages.core.models import WordTimestamp

def format_timestamp_srt(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours = millis // 3_600_000
    millis %= 3_600_000
    minutes = millis // 60_000
    millis %= 60_000
    secs = millis // 1_000
    millis %= 1_000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def format_timestamp_vtt(seconds: float) -> str:
    return format_timestamp_srt(seconds).replace(",", ".")

class CaptionsGenerator:
    """Creates formatted subtitles (.srt, .vtt) from word timestamps."""

    @classmethod
    def generate_srt_from_words(
        cls,
        words: List[Union[Dict[str, Any], WordTimestamp]],
        max_words_per_cue: int = 5,
        max_duration_seconds: float = 3.0,
    ) -> str:
        if not words:
            return ""

        cues = []
        current_cue_words = []
        cue_start = None

        for w in words:
            if isinstance(w, WordTimestamp):
                word_text = w.word.strip()
                w_start = w.start
                w_end = w.end
            else:
                word_text = w.get("word", w.get("text", "")).strip()
                w_start = float(w.get("start", 0.0))
                w_end = float(w.get("end", 0.0))

            if cue_start is None:
                cue_start = w_start

            current_cue_words.append(word_text)

            is_long_enough = (w_end - cue_start) >= max_duration_seconds
            is_word_limit = len(current_cue_words) >= max_words_per_cue
            is_sentence_end = word_text.endswith((".", "!", "?"))

            if is_long_enough or is_word_limit or is_sentence_end:
                cues.append({
                    "start": cue_start,
                    "end": w_end,
                    "text": " ".join(current_cue_words),
                })
                current_cue_words = []
                cue_start = None

        if current_cue_words and cue_start is not None:
            last_w = words[-1]
            last_end = last_w.end if isinstance(last_w, WordTimestamp) else last_w.get("end", cue_start + 1.0)
            cues.append({
                "start": cue_start,
                "end": last_end,
                "text": " ".join(current_cue_words),
            })

        lines = []
        for i, cue in enumerate(cues, 1):
            start_str = format_timestamp_srt(cue["start"])
            end_str = format_timestamp_srt(cue["end"])
            lines.append(f"{i}\n{start_str} --> {end_str}\n{cue['text']}\n")

        return "\n".join(lines)

    @classmethod
    def generate_vtt_from_words(
        cls,
        words: List[Union[Dict[str, Any], WordTimestamp]],
        max_words_per_cue: int = 5,
        max_duration_seconds: float = 3.0,
    ) -> str:
        srt = cls.generate_srt_from_words(words, max_words_per_cue, max_duration_seconds)
        if not srt:
            return "WEBVTT\n\n"
        vtt = srt.replace(",", ".")
        return "WEBVTT\n\n" + vtt

def generate_srt(words: List[Union[Dict[str, Any], WordTimestamp]], output_path: Union[str, Path]) -> Path:
    srt_text = CaptionsGenerator.generate_srt_from_words(words)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(srt_text, encoding="utf-8")
    return out

def generate_vtt(words: List[Union[Dict[str, Any], WordTimestamp]], output_path: Union[str, Path]) -> Path:
    vtt_text = CaptionsGenerator.generate_vtt_from_words(words)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(vtt_text, encoding="utf-8")
    return out
