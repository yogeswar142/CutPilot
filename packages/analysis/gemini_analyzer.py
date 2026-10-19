"""
CutPilot Gemini Visual Analyzer
Submits silent video proxies or keyframe assets to Google Gemini for structured video understanding.
"""
import os
import json
import base64
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional, List
from packages.core.models import VisualAnalysisResult, VisualEvent
from packages.core.config import settings

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

def parse_time_str(ts: str) -> float:
    """Parses 'MM:SS.S' or float string into seconds."""
    if not ts:
        return 0.0
    ts = ts.strip().replace(",", ".")
    if ":" in ts:
        parts = ts.split(":")
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    try:
        return float(ts)
    except ValueError:
        return 0.0

PROMPT_TEXT = (
    "Analyze the visual events in this video screen recording. "
    "Output concise, valid JSON with the following structure:\n"
    "{\n"
    '  "visual_events": [\n'
    "    {\n"
    '      "start_timestamp": "MM:SS.S",\n'
    '      "end_timestamp": "MM:SS.S",\n'
    '      "event_type": "ui_transition" | "slide_change" | "speaker_action" | "scene_cut",\n'
    '      "event_description": "summary of visual change",\n'
    '      "on_screen_text": "any readable text or code",\n'
    '      "evidence": "visible visual cues",\n'
    '      "confidence": 0.0 to 1.0\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "Do not include audio assumptions. Base all observations strictly on visual evidence."
)

def analyze_video_gemini(video_path: str, model_id: str = "gemini-2.5-flash") -> VisualAnalysisResult:
    """
    Analyzes video via Gemini API and parses into structured VisualAnalysisResult.
    """
    key = settings.gemini_api_key
    if not key:
        raise ValueError("GEMINI_API_KEY is not configured in environment or settings.")

    video_file = Path(video_path).resolve()
    if not video_file.is_file():
        raise FileNotFoundError(f"Video file not found: {video_file}")

    with open(video_file, "rb") as f:
        video_bytes = f.read()

    b64_video = base64.b64encode(video_bytes).decode("utf-8")
    url = f"{API_BASE}/{model_id}:generateContent?key={key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT_TEXT},
                    {
                        "inline_data": {
                            "mime_type": "video/mp4",
                            "data": b64_video
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp_bytes = resp.read()
            resp_json = json.loads(resp_bytes.decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        raise RuntimeError(f"Gemini API request failed ({e.code}): {err_msg}") from e

    # Parse response
    candidates = resp_json.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")

    part = candidates[0].get("content", {}).get("parts", [{}])[0]
    content_text = part.get("text", "{}")
    parsed_content = json.loads(content_text)

    raw_events = parsed_content.get("visual_events", [])
    events = []

    for i, ev in enumerate(raw_events):
        start_s = parse_time_str(ev.get("start_timestamp", "0:00"))
        end_s = parse_time_str(ev.get("end_timestamp", "0:00"))
        conf = float(ev.get("confidence", 1.0)) if isinstance(ev.get("confidence"), (int, float)) else 0.9

        events.append(VisualEvent(
            id=f"ve_{i:03d}",
            start_seconds=start_s,
            end_seconds=end_s,
            event_type=ev.get("event_type", "ui_transition"),
            description=ev.get("event_description", ""),
            on_screen_text=ev.get("on_screen_text"),
            confidence=conf,
            evidence=ev.get("evidence", "")
        ))

    return VisualAnalysisResult(
        source_media=str(video_file),
        model_id=model_id,
        events=events,
        version="1.0.0",
        raw_response=resp_json
    )
