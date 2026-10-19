"""
Unit Tests for CutPilot Core Models
"""
import pytest
from packages.core.models import (
    MediaAsset,
    WordTimestamp,
    TranscriptSegment,
    TranscriptResult,
    EditAction,
    EditPlan,
)

def test_media_asset_serialization():
    asset = MediaAsset(
        file_path="C:/videos/test.mp4",
        file_name="test.mp4",
        file_size_bytes=1024,
        duration_seconds=15.267,
        fps=30.0,
        width=1280,
        height=720,
        total_frames=458
    )
    d = asset.to_dict()
    assert d["fps"] == 30.0
    assert d["file_name"] == "test.mp4"
    assert d["total_frames"] == 458

    reconstructed = MediaAsset.from_dict(d)
    assert reconstructed.duration_seconds == 15.267
    assert reconstructed.total_frames == 458

def test_transcript_result_serialization():
    w1 = WordTimestamp(word="Hello", start=0.5, end=0.8, confidence=0.98)
    w2 = WordTimestamp(word="world", start=0.85, end=1.2, confidence=0.95)
    seg = TranscriptSegment(id=1, start=0.5, end=1.2, text="Hello world", words=[w1, w2])
    transcript = TranscriptResult(
        source_media="test.mp4",
        duration_seconds=15.0,
        segments=[seg]
    )

    d = transcript.to_dict()
    assert len(d["segments"]) == 1
    assert len(d["segments"][0]["words"]) == 2

    reconstructed = TranscriptResult.from_dict(d)
    assert len(reconstructed.segments[0].words) == 2
    assert reconstructed.segments[0].words[0].word == "Hello"

def test_edit_plan_serialization():
    action = EditAction(
        action_type="append",
        source_clip="test.mp4",
        start_frame=0,
        end_frame=72,
        track_type="video",
        track_index=1
    )
    plan = EditPlan(
        project_name="Canary",
        timeline_name="Timeline 1",
        target_fps=24.0,
        source_assets=["test.mp4"],
        actions=[action]
    )

    d = plan.to_dict()
    assert d["project_name"] == "Canary"
    assert len(d["actions"]) == 1

    reconstructed = EditPlan.from_dict(d)
    assert reconstructed.actions[0].end_frame == 72
