"""
CutPilot Agent 2 — Visual Analysis & Understanding
Coordinates keyframe extraction, OCR, and cloud video understanding via Gemini.
"""
from typing import Optional, Dict, Any, List
from packages.core.models import VisualAnalysisResult
from packages.analysis.gemini_analyzer import analyze_video_gemini
from packages.analysis.keyframe_selector import select_keyframes
from packages.media.video import create_silent_proxy

def run_agent2_visual_analysis(
    video_path: str,
    model_id: str = "gemini-2.5-flash",
    extract_local_keyframes: bool = True,
    temp_dir: Optional[str] = None
) -> Tuple[VisualAnalysisResult, List[Dict[str, Any]]]:
    """
    Executes Agent 2 workflow:
    1. Optionally extracts adaptive keyframes locally.
    2. Submits silent proxy to Gemini Cloud Video API for structured visual events.
    """
    keyframes = []
    if extract_local_keyframes:
        kf_dir = temp_dir if temp_dir else "artifacts/temporary/keyframes"
        keyframes = select_keyframes(video_path, kf_dir)

    visual_result = analyze_video_gemini(video_path, model_id=model_id)
    return visual_result, keyframes
