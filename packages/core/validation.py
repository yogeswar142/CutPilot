"""
CutPilot Core Validation
Strict validators for transcripts, word timestamps, media bounds, and edit plans.
"""
from typing import List, Dict, Tuple, Any
from packages.core.models import TranscriptResult, EditPlan, MediaAsset

class ValidationError(ValueError):
    """Raised when data fails strict CutPilot safety invariants."""
    pass

def validate_transcript_bounds(transcript: TranscriptResult, media_duration: float, tolerance: float = 0.05) -> Tuple[bool, List[str]]:
    """
    Validates that word and segment timestamps do not exceed the actual media duration.
    Flags any out-of-bounds timestamp rather than silently clipping it.
    """
    issues = []
    max_allowed = media_duration + tolerance

    for seg in transcript.segments:
        if seg.start < 0:
            issues.append(f"Segment {seg.id} start ({seg.start:.3f}s) is negative.")
        if seg.end > max_allowed:
            issues.append(f"Segment {seg.id} end ({seg.end:.3f}s) exceeds media duration ({media_duration:.3f}s).")
        if seg.start > seg.end:
            issues.append(f"Segment {seg.id} start ({seg.start:.3f}s) > end ({seg.end:.3f}s).")

        for w in seg.words:
            if w.start < 0:
                issues.append(f"Word '{w.word}' start ({w.start:.3f}s) is negative in segment {seg.id}.")
            if w.end > max_allowed:
                issues.append(f"Word '{w.word}' end ({w.end:.3f}s) exceeds media duration ({media_duration:.3f}s) in segment {seg.id}.")
            if w.start > w.end:
                issues.append(f"Word '{w.word}' start ({w.start:.3f}s) > end ({w.end:.3f}s) in segment {seg.id}.")

    is_valid = len(issues) == 0
    return is_valid, issues

def validate_edit_plan(plan: EditPlan, media_assets: Dict[str, MediaAsset] = None) -> Tuple[bool, List[str]]:
    """
    Validates that an EditPlan is internally consistent and within bounds of referenced media assets.
    """
    issues = []

    if not plan.project_name or not plan.project_name.strip():
        issues.append("EditPlan must specify a non-empty project_name.")
    if not plan.timeline_name or not plan.timeline_name.strip():
        issues.append("EditPlan must specify a non-empty timeline_name.")
    if plan.target_fps <= 0:
        issues.append(f"Invalid target_fps: {plan.target_fps}. Must be > 0.")
    if not plan.actions:
        issues.append("EditPlan contains no actions.")

    for i, action in enumerate(plan.actions):
        if action.start_frame < 0:
            issues.append(f"Action #{i} ({action.action_type}) start_frame is negative: {action.start_frame}")
        if action.end_frame < action.start_frame:
            issues.append(f"Action #{i} ({action.action_type}) end_frame ({action.end_frame}) < start_frame ({action.start_frame})")

        if media_assets and action.source_clip in media_assets:
            asset = media_assets[action.source_clip]
            if asset.total_frames and action.end_frame > asset.total_frames:
                issues.append(f"Action #{i} end_frame ({action.end_frame}) exceeds source frames ({asset.total_frames}) for '{action.source_clip}'")

    is_valid = len(issues) == 0
    return is_valid, issues
