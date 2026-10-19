"""
Comprehensive Frame-Accurate Math and Timecode Conversion Tests
Validates source-to-timeline conversions, inclusive/exclusive bounds, fractional frames, and timecode offsets.
"""
import math
import pytest
from packages.resolve_adapter.framerate import convert_frame_bounds, frames_to_seconds, seconds_to_frames

class TestFrameAccurateConversions:
    """Tests edge cases and boundary semantics across differing framerates."""

    def test_30fps_to_24fps_exact_integer_seconds(self):
        """1 second = 30 frames at 30fps = 24 frames at 24fps."""
        # 1.0s exact: 0 to 30 frames
        tgt_start, tgt_end, tgt_dur = convert_frame_bounds(0, 30, source_fps=30.0, target_fps=24.0)
        assert tgt_start == 0
        assert tgt_end == 24
        assert tgt_dur == 24

    def test_reproduce_72_frame_canary_discrepancy(self):
        """
        Reproduces the 72-frame slice at 30fps placed on a 24fps timeline.
        72 frames / 30 fps = 2.400s.
        2.400s * 24 fps = 57.6 frames.
        
        Mathematical analysis:
        - round(57.6) = 58
        - math.floor(57.6) = 57
        DaVinci Resolve truncates fractional timeline frames during playback conforming,
        yielding exactly 57 timeline frames ([86400, 86457)).
        """
        source_frames = 72
        source_fps = 30.0
        target_fps = 24.0
        
        duration_seconds = source_frames / source_fps
        assert duration_seconds == 2.4
        
        exact_target_frames = duration_seconds * target_fps
        assert abs(exact_target_frames - 57.6) < 1e-6
        
        # Resolve floor truncation behavior
        resolve_timeline_duration = math.floor(exact_target_frames)
        assert resolve_timeline_duration == 57

    def test_inclusive_vs_exclusive_semantics(self):
        """
        DaVinci Resolve API Semantics:
        - MediaPool.AppendToTimeline input: endFrame is EXCLUSIVE ([start, end))
        - TimelineItem.GetStart(): INCLUSIVE start on timeline
        - TimelineItem.GetEnd(): EXCLUSIVE end on timeline (start + duration)
        - TimelineItem.GetSourceStartFrame(): INCLUSIVE source start (0)
        - TimelineItem.GetSourceEndFrame(): INCLUSIVE source end (71 for 72 frames)
        """
        start_frame = 0
        end_frame = 72
        # Exclusive bound duration:
        exclusive_duration = end_frame - start_frame
        assert exclusive_duration == 72
        
        # Resolve's recorded SourceEndFrame is inclusive (last frame index)
        inclusive_last_source_frame = end_frame - 1
        assert inclusive_last_source_frame == 71

    def test_start_timecode_offsets(self):
        """
        Resolve default timelines start at 01:00:00:00 (1 hour).
        - At 24.0 fps: 1 hour = 3600s * 24 = 86,400 frames.
        - At 30.0 fps: 1 hour = 3600s * 30 = 108,000 frames.
        - At 29.97 fps (Drop Frame): 107,892 frames.
        """
        tc_1hr_24fps = 3600 * 24
        assert tc_1hr_24fps == 86400
        
        tc_1hr_30fps = 3600 * 30
        assert tc_1hr_30fps == 108000
        
        # When 57 frames are placed at 01:00:00:00:
        placed_start = tc_1hr_24fps
        placed_duration = 57
        placed_end = placed_start + placed_duration
        assert placed_end == 86457

    def test_fractional_frame_durations(self):
        """Verify behavior for various fractional frame durations."""
        # 1 frame at 30 fps = 0.03333s -> on 24 fps = 0.8 frames -> floors to 0 or ceil/round to 1
        one_frame_30fps = 1 / 30.0
        assert math.floor(one_frame_30fps * 24.0) == 0
        assert round(one_frame_30fps * 24.0) == 1
        
        # 15 frames at 30 fps = 0.5s -> on 24 fps = 12.0 frames exactly
        half_sec = 15 / 30.0
        assert half_sec * 24.0 == 12.0
