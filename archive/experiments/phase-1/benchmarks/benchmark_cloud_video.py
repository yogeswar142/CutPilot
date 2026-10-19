"""
CutPilot Phase 2.3 — Native Cloud Video Understanding Benchmark Script

Evaluates native cloud video understanding via Google's Gemini API:
- Primary model: `gemini-3.5-flash-lite` (per user request for free tier quota efficiency)
- Reference model: `gemini-3.8-flash`
- Input media: `phase-1/outputs/test-15s-silent.mp4` (audio stripped to evaluate purely visual understanding)
- Strict rule: Read `GEMINI_API_KEY` from environment. Never print or store it.
- Generates structured JSON responses and sanitized performance telemetry.
"""

import os
import sys
import time
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
TEST_RESULTS_DIR = BASE_DIR / "test-results"

SILENT_VIDEO_PATH = OUTPUTS_DIR / "test-15s-silent.mp4"
RAW_RESPONSES_PATH = TEST_RESULTS_DIR / "gemini_cloud_responses.json"
BENCHMARK_METRICS_PATH = TEST_RESULTS_DIR / "gemini_benchmark_metrics.json"

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as reg_key:
                key, _ = winreg.QueryValueEx(reg_key, "GEMINI_API_KEY")
                os.environ["GEMINI_API_KEY"] = key
        except Exception:
            pass
    if not key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please configure it.")
    return key


PROMPT_TEXT = (
    "Analyze the visual events in this video screen recording. "
    "Output concise, valid JSON with the following structure:\n"
    "{\n"
    '  "visual_events": [\n'
    "    {\n"
    '      "start_timestamp": "MM:SS.S",\n'
    '      "end_timestamp": "MM:SS.S",\n'
    '      "event_description": "summary of event",\n'
    '      "ui_state_changes": "state changes in UI",\n'
    '      "visible_actions": "gestures or user actions",\n'
    '      "on_screen_text": ["exact readable text 1", "exact readable text 2"],\n'
    '      "evidence": "visual visual cues supporting this",\n'
    '      "confidence": "HIGH/MEDIUM/LOW with explanation"\n'
    "    }\n"
    "  ],\n"
    '  "moments_requiring_precise_inspection": [\n'
    '    {"timestamp": "MM:SS.S", "reason": "why frame-by-frame inspection is needed"}\n'
    "  ],\n"
    '  "overall_summary": "1-2 sentence visual summary"\n'
    "}\n"
    "Do not include audio assumptions or dialogue. Base all observations strictly on visual evidence."
)


def call_gemini_video(model_id: str, video_bytes: bytes, prompt: str, key: str, timeout=120):
    url = f"{API_BASE}/{model_id}:generateContent?key={key}"
    b64_video = base64.b64encode(video_bytes).decode("utf-8")
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
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
    
    t0 = time.perf_counter()
    status_code = None
    response_json = None
    error_msg = None
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.status
            body = resp.read().decode("utf-8")
            response_json = json.loads(body)
    except urllib.error.HTTPError as e:
        status_code = e.code
        error_msg = e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        error_msg = str(e)
        
    elapsed = time.perf_counter() - t0
    
    return {
        "model_id": model_id,
        "status_code": status_code,
        "elapsed_seconds": round(elapsed, 3),
        "response_json": response_json,
        "error_msg": error_msg
    }


def parse_and_validate_response(call_result):
    resp = call_result.get("response_json")
    if not resp:
        return {
            "success": False,
            "error": call_result.get("error_msg", "No response body"),
            "is_valid_json": False,
            "parsed_content": None,
            "usage": None
        }
        
    cand = resp.get("candidates", [{}])[0]
    content_parts = cand.get("content", {}).get("parts", [])
    raw_text = content_parts[0].get("text", "") if content_parts else ""
    finish_reason = cand.get("finishReason")
    usage = resp.get("usageMetadata", {})
    
    is_valid_json = False
    parsed = None
    try:
        parsed = json.loads(raw_text)
        is_valid_json = True
    except Exception:
        pass
        
    return {
        "success": call_result["status_code"] == 200,
        "finish_reason": finish_reason,
        "raw_text": raw_text,
        "is_valid_json": is_valid_json,
        "parsed_content": parsed,
        "usage": usage
    }


def main():
    print("=== CutPilot Phase 2.3: Native Cloud Video Understanding Benchmark ===")
    TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Verify key
    key = get_api_key()
    print("API Key loaded from environment successfully.")
    
    # 2. Check input video
    if not SILENT_VIDEO_PATH.exists():
        print(f"Error: Silent video file not found at {SILENT_VIDEO_PATH}")
        sys.exit(1)
        
    with open(SILENT_VIDEO_PATH, "rb") as f:
        video_bytes = f.read()
    video_size_mb = len(video_bytes) / (1024 * 1024)
    print(f"Input video: {SILENT_VIDEO_PATH.name} ({video_size_mb:.2f} MB, pure video, 0 audio)")
    
    # 3. Model Runs Plan:
    # Primary: gemini-3.5-flash-lite (3 runs to measure median, variability, and quota consistency)
    # Reference: gemini-3.8-flash (1 run to measure quality, thinking tokens, and latency delta)
    test_suite = [
        {"model": "gemini-3.5-flash-lite", "run_id": "gemini-3.5-flash-lite_run1"},
        {"model": "gemini-3.5-flash-lite", "run_id": "gemini-3.5-flash-lite_run2"},
        {"model": "gemini-3.5-flash-lite", "run_id": "gemini-3.5-flash-lite_run3"},
        {"model": "gemini-3.8-flash", "run_id": "gemini-3.8-flash_run1"}
    ]
    
    all_runs = []
    saved_raw_responses = {}
    
    for item in test_suite:
        m = item["model"]
        rid = item["run_id"]
        print(f"\n>>> Executing Test [{rid}] on {m}...")
        
        call_res = call_gemini_video(m, video_bytes, PROMPT_TEXT, key)
        parsed_res = parse_and_validate_response(call_res)
        
        run_record = {
            "run_id": rid,
            "model_id": m,
            "status_code": call_res["status_code"],
            "success": parsed_res["success"],
            "elapsed_seconds": call_res["elapsed_seconds"],
            "finish_reason": parsed_res.get("finish_reason"),
            "is_valid_json": parsed_res["is_valid_json"],
            "usage": parsed_res["usage"],
            "error": call_res.get("error_msg")
        }
        
        print(f"Status: {call_res['status_code']} | Time: {call_res['elapsed_seconds']:.2f}s | Valid JSON: {parsed_res['is_valid_json']}")
        if parsed_res["usage"]:
            u = parsed_res["usage"]
            prompt_tok = u.get("promptTokenCount", 0)
            cand_tok = u.get("candidatesTokenCount", 0)
            thought_tok = u.get("thoughtsTokenCount", 0)
            tot_tok = u.get("totalTokenCount", 0)
            print(f"Tokens: Prompt={prompt_tok} (Video ~990), Generated={cand_tok}, Thoughts={thought_tok}, Total={tot_tok}")
            
        all_runs.append(run_record)
        saved_raw_responses[rid] = {
            "model": m,
            "elapsed_seconds": call_res["elapsed_seconds"],
            "usage": parsed_res["usage"],
            "parsed_content": parsed_res["parsed_content"],
            "raw_text": parsed_res.get("raw_text")
        }
        
        # Brief delay to respect free tier rate limit window
        time.sleep(2.0)
        
    # Save sanitized records
    with open(BENCHMARK_METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_runs, f, indent=2)
    print(f"\nSaved benchmark metrics to {BENCHMARK_METRICS_PATH}")
    
    with open(RAW_RESPONSES_PATH, "w", encoding="utf-8") as f:
        json.dump(saved_raw_responses, f, indent=2)
    print(f"Saved sanitized raw responses to {RAW_RESPONSES_PATH}")
    print("Cloud Video Benchmark execution completed successfully.")


if __name__ == "__main__":
    main()
