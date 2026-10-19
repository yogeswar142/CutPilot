"""
CutPilot Editing Package
FCPXML (xmeml v4) timeline generation, SRT/VTT caption creation, and edit plan execution.
"""
from packages.editing.captions import CaptionsGenerator, generate_srt, generate_vtt
from packages.editing.fcpxml import FcpXmlGenerator, CutPlan, PartSource, ClipSegment, BlackSegment, generate_fcpxml
from packages.editing.plan_executor import execute_edit_plan

__all__ = [
    "CaptionsGenerator",
    "generate_srt",
    "generate_vtt",
    "FcpXmlGenerator",
    "CutPlan",
    "PartSource",
    "ClipSegment",
    "BlackSegment",
    "generate_fcpxml",
    "execute_edit_plan",
]
