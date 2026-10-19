"""
CutPilot Agent 3 — Edit Plan Generation & Synthesis
Merges transcript word timing and visual event cues into a verified, deterministic EditPlan.
Enforces the safety boundary: Agent 3 generates structured plans; it never executes arbitrary NLE calls directly.
"""
from typing import List, Dict, Any, Optional
import time
from packages.core.models import EditPlan, EditAction, TranscriptResult, VisualAnalysisResult
from packages.resolve_adapter.framerate import seconds_to_frames

def generate_rough_cut_plan(
    video_path: str,
    transcript: TranscriptResult,
    visual_analysis: Optional[VisualAnalysisResult] = None,
    project_name: str = "CutPilot_Project",
    timeline_name: str = "Rough_Cut_Timeline",
    target_fps: float = 24.0,
    head_pad_seconds: float = 0.1,
    tail_pad_seconds: float = 0.15,
) -> EditPlan:
    """
    Synthesizes speech segments into a rough-cut sequence with padding handles,
    eliminating long silences while preserving complete words.
    """
    actions: List[EditAction] = []

    for seg in transcript.segments:
        if not seg.words or not seg.text.strip():
            continue

        first_word = seg.words[0]
        last_word = seg.words[-1]

        # Apply padding handles
        cut_start_s = max(0.0, first_word.start - head_pad_seconds)
        cut_end_s = min(transcript.duration_seconds, last_word.end + tail_pad_seconds)

        start_frame = seconds_to_frames(cut_start_s, target_fps)
        end_frame = seconds_to_frames(cut_end_s, target_fps)

        if end_frame <= start_frame:
            end_frame = start_frame + 1

        actions.append(EditAction(
            action_type="append",
            source_clip=video_path,
            start_frame=start_frame,
            end_frame=end_frame,
            track_type="video",
            track_index=1,
            caption_text=seg.text
        ))

    return EditPlan(
        project_name=project_name,
        timeline_name=timeline_name,
        target_fps=target_fps,
        source_assets=[video_path],
        actions=actions,
        schema_version="1.0.0",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        notes=f"Generated {len(actions)} speech segments with {head_pad_seconds}s head and {tail_pad_seconds}s tail padding."
    )
