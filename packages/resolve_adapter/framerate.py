"""
CutPilot Frame Rate & Timecode Alignment
Resolves framerate discrepancies between source media (e.g. 30 fps) and Resolve timelines (e.g. 24 fps).
"""
import math
from typing import Tuple

def seconds_to_frames(seconds: float, fps: float, method: str = "floor") -> int:
    """
    Converts seconds to integer frames.
    method: 'floor' (DaVinci Resolve conforming default), 'round', or 'ceil'.
    """
    val = seconds * fps
    if method == "floor":
        return int(math.floor(val))
    elif method == "ceil":
        return int(math.ceil(val))
    return int(round(val))

def frames_to_seconds(frames: int, fps: float) -> float:
    return frames / fps if fps > 0 else 0.0

def convert_frame_bounds(
    start_frame: int,
    end_frame: int,
    source_fps: float,
    target_fps: float,
    method: str = "floor",
) -> Tuple[int, int, int]:
    """
    Translates a frame range from source FPS to target timeline FPS.
    Returns (target_start, target_end, target_duration).
    
    Default method='floor' matches DaVinci Resolve's timeline conforming behavior:
    72 source frames at 30 fps is 2.400 seconds.
    On a 24 fps timeline: 2.400 * 24 = 57.6 -> floor(57.6) = 57 frames.
    """
    if abs(source_fps - target_fps) < 0.001:
        return start_frame, end_frame, end_frame - start_frame

    start_seconds = frames_to_seconds(start_frame, source_fps)
    end_seconds = frames_to_seconds(end_frame, source_fps)

    target_start = seconds_to_frames(start_seconds, target_fps, method=method)
    target_end = seconds_to_frames(end_seconds, target_fps, method=method)
    target_duration = target_end - target_start

    return target_start, target_end, target_duration
