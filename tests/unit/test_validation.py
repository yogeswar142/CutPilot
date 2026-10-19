"""
Unit Tests for CutPilot Core Validation
"""
import pytest
from packages.core.models import TranscriptResult, TranscriptSegment, WordTimestamp, EditPlan, EditAction
from packages.core.validation import validate_transcript_bounds, validate_edit_plan

def test_validate_transcript_within_bounds():
    w = WordTimestamp(word="test", start=1.0, end=2.0)
    seg = TranscriptSegment(id=0, start=1.0, end=2.0, text="test", words=[w])
    tr = TranscriptResult(source_media="test.mp4", duration_seconds=15.267, segments=[seg])

    valid, issues = validate_transcript_bounds(tr, media_duration=15.267)
    assert valid is True
    assert len(issues) == 0

def test_validate_transcript_exceeding_bounds():
    # Word ends at 16.0s on a 15.267s video
    w = WordTimestamp(word="overflow", start=14.0, end=16.0)
    seg = TranscriptSegment(id=0, start=14.0, end=16.0, text="overflow", words=[w])
    tr = TranscriptResult(source_media="test.mp4", duration_seconds=15.267, segments=[seg])

    valid, issues = validate_transcript_bounds(tr, media_duration=15.267)
    assert valid is False
    assert any("exceeds media duration" in issue for issue in issues)

def test_validate_edit_plan_valid():
    action = EditAction(action_type="append", source_clip="test.mp4", start_frame=0, end_frame=100)
    plan = EditPlan(project_name="P1", timeline_name="T1", target_fps=24.0, source_assets=["test.mp4"], actions=[action])

    valid, issues = validate_edit_plan(plan)
    assert valid is True
    assert len(issues) == 0

def test_validate_edit_plan_invalid_frames():
    # start_frame > end_frame
    action = EditAction(action_type="append", source_clip="test.mp4", start_frame=200, end_frame=100)
    plan = EditPlan(project_name="P1", timeline_name="T1", target_fps=24.0, source_assets=["test.mp4"], actions=[action])

    valid, issues = validate_edit_plan(plan)
    assert valid is False
    assert any("end_frame (100) < start_frame (200)" in issue for issue in issues)
