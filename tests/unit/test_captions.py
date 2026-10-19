"""
Unit Tests for CutPilot Captions Generator
"""
import pytest
from packages.editing.captions import CaptionsGenerator, format_timestamp_srt, format_timestamp_vtt
from packages.core.models import WordTimestamp

def test_timestamp_formatting():
    assert format_timestamp_srt(0.0) == "00:00:00,000"
    assert format_timestamp_srt(65.123) == "00:01:05,123"
    assert format_timestamp_vtt(65.123) == "00:01:05.123"

def test_generate_srt_from_word_objects():
    words = [
        WordTimestamp(word="This", start=0.0, end=0.3),
        WordTimestamp(word="is", start=0.35, end=0.5),
        WordTimestamp(word="a", start=0.55, end=0.7),
        WordTimestamp(word="test.", start=0.75, end=1.1),
    ]
    srt = CaptionsGenerator.generate_srt_from_words(words, max_words_per_cue=5)
    assert "1" in srt
    assert "00:00:00,000 --> 00:00:01,100" in srt
    assert "This is a test." in srt

def test_generate_vtt_header():
    words = [WordTimestamp(word="Hello", start=0.1, end=0.5)]
    vtt = CaptionsGenerator.generate_vtt_from_words(words)
    assert vtt.startswith("WEBVTT")
    assert "Hello" in vtt
