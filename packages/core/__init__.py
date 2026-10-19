"""
CutPilot Core Package
Shared data contracts, configuration, and validation logic.
"""
from packages.core.models import (
    MediaAsset,
    WordTimestamp,
    TranscriptSegment,
    TranscriptResult,
    VisualEvent,
    VisualAnalysisResult,
    EditAction,
    EditPlan,
    OperationRecord,
    TimelineVerificationResult,
)
from packages.core.config import settings
from packages.core.validation import validate_transcript_bounds, validate_edit_plan

__all__ = [
    "MediaAsset",
    "WordTimestamp",
    "TranscriptSegment",
    "TranscriptResult",
    "VisualEvent",
    "VisualAnalysisResult",
    "EditAction",
    "EditPlan",
    "OperationRecord",
    "TimelineVerificationResult",
    "settings",
    "validate_transcript_bounds",
    "validate_edit_plan",
]
