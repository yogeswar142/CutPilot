"""
CutPilot Keyframe Selector
Adaptive scene-cut detection and perceptual frame-difference extraction.
"""
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Any
from packages.core.config import settings
from packages.media.inspector import inspect_media
from packages.media.video import extract_frame

def select_keyframes(video_path: str, output_dir: str, threshold: float = 0.15) -> List[Dict[str, Any]]:
    """
    Selects adaptive keyframes based on scene cuts and frame changes.
    Guarantees retention of beginning and end frames.
    """
    asset = inspect_media(video_path)
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(settings.ffmpeg_path),
        "-i", str(Path(video_path).resolve()),
        "-filter:v", f"select='gt(scene,{threshold})',metadata=print:file=-",
        "-f", "null",
        "-"
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    raw_output = res.stderr + "\n" + res.stdout

    detected_pts = []
    for line in raw_output.splitlines():
        if "pts_time:" in line:
            m = re.search(r"pts_time:([0-9\.]+)", line)
            if m:
                pts = float(m.group(1))
                if pts not in detected_pts:
                    detected_pts.append(pts)

    # Ensure beginning (0.0s) and near-end are included
    timestamps = [0.0]
    for ts in sorted(detected_pts):
        if ts > 0.5 and (asset.duration_seconds - ts) > 0.5:
            timestamps.append(round(ts, 3))
    
    end_anchor = max(0.0, round(asset.duration_seconds - 0.2, 3))
    if end_anchor > timestamps[-1] + 0.5:
        timestamps.append(end_anchor)

    keyframe_records = []
    for i, ts in enumerate(timestamps):
        frame_name = f"keyframe_{i:02d}_{ts:.2f}s.jpg"
        frame_path = out_dir / frame_name
        extract_frame(video_path, ts, str(frame_path))
        keyframe_records.append({
            "index": i,
            "timestamp_seconds": ts,
            "frame_path": str(frame_path),
            "frame_name": frame_name
        })

    return keyframe_records
