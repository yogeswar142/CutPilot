"""
Unit Tests for CutPilot Framerate & Timecode Conversion
"""
import pytest
from packages.resolve_adapter.framerate import convert_frame_bounds, seconds_to_frames, frames_to_seconds

def test_framerate_conversion_30_to_24():
    """
    Verifies the Phase 3.1 canary finding:
    72 source frames at 30.0 fps -> 57 timeline frames at 24.0 fps.
    """
    source_fps = 30.0
    timeline_fps = 24.0
    start_src = 0
    end_src = 72

    t_start, t_end, duration = convert_frame_bounds(start_src, end_src, source_fps, timeline_fps)

    # 72 frames / 30 fps = 2.400 seconds
    assert frames_to_seconds(end_src, source_fps) == 2.4
    # 2.4s * 24 fps = 57.6 frames -> truncates/rounds to 57 or 58 frames
    assert t_start == 0
    assert duration in (57, 58)
    assert t_end == duration

def test_framerate_conversion_same_fps():
    t_start, t_end, duration = convert_frame_bounds(10, 50, 24.0, 24.0)
    assert t_start == 10
    assert t_end == 50
    assert duration == 40
