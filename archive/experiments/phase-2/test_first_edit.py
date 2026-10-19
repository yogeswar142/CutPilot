"""
CutPilot Phase 3.1 - First Verified Timeline Edit
Tests the smallest safe, reversible timeline-editing workflow on DaVinci Resolve Free 21.0.3.7.
"""
import sys
import os
import json
import time
from pathlib import Path

# Add davinci-resolve-mcp to path
MCP_REPO = Path(__file__).resolve().parent / "reference" / "davinci-resolve-mcp"
sys.path.insert(0, str(MCP_REPO))

from src.utils import resolve_bridge_client

CANARY_PROJECT_NAME = "CutPilot_Canary"
TEST_MEDIA_PATH = str(Path(__file__).resolve().parent.parent / "phase-1" / "assets" / "test-15s.mp4")
TIMELINE_NAME = "Canary_Timeline_01"

def log_event(events, step, status, details=None):
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "step": step,
        "status": status,
        "details": details or {}
    }
    events.append(entry)
    print(f"[{entry['timestamp']}] [{step}] {status}: {json.dumps(details or {}, default=str)}")
    return entry

def run_canary_edit():
    events = []
    summary = {
        "status": "FAILED",
        "canary_project": CANARY_PROJECT_NAME,
        "operations_tested": [],
        "timeline_verification": None,
        "error": None
    }
    
    print("=" * 70)
    print("CutPilot Phase 3.1: First Verified Timeline Edit Test")
    print("=" * 70)
    
    # Precondition: media exists
    if not os.path.isfile(TEST_MEDIA_PATH):
        err = f"Test media file not found at: {TEST_MEDIA_PATH}"
        log_event(events, "precondition_media", "FAILED", {"error": err})
        summary["error"] = err
        return summary, events
    log_event(events, "precondition_media", "PASS", {"path": TEST_MEDIA_PATH, "size": os.path.getsize(TEST_MEDIA_PATH)})

    # Step 1: Connect to bridge
    try:
        resolve = resolve_bridge_client.connect(require_enabled=False, timeout=10.0)
        pm = resolve.GetProjectManager()
        if not pm:
            raise RuntimeError("GetProjectManager returned None")
        log_event(events, "connect_bridge", "PASS", {"product": resolve.GetProductName(), "version": resolve.GetVersionString()})
    except Exception as e:
        err = f"Failed to connect to Resolve bridge: {e}"
        log_event(events, "connect_bridge", "FAILED", {"error": err})
        summary["error"] = err
        return summary, events

    # Step 2: Check current project before anything
    try:
        initial_project = pm.GetCurrentProject()
        initial_name = initial_project.GetName() if initial_project else None
        log_event(events, "initial_project_check", "PASS", {"active_project": initial_name})
    except Exception as e:
        err = f"Failed to inspect initial project: {e}"
        log_event(events, "initial_project_check", "FAILED", {"error": err})
        summary["error"] = err
        return summary, events

    # Step 3: Explicit project targeting (Create or Load CutPilot_Canary)
    try:
        projects = pm.GetProjectListInCurrentFolder() or []
        log_event(events, "list_projects", "PASS", {"projects": projects})
        
        canary_proj = None
        if CANARY_PROJECT_NAME in projects:
            print(f"Project '{CANARY_PROJECT_NAME}' already exists. Loading it...")
            canary_proj = pm.LoadProject(CANARY_PROJECT_NAME)
            summary["operations_tested"].append("pm.LoadProject")
        else:
            print(f"Creating project '{CANARY_PROJECT_NAME}'...")
            canary_proj = pm.CreateProject(CANARY_PROJECT_NAME)
            summary["operations_tested"].append("pm.CreateProject")
            
        if not canary_proj:
            raise RuntimeError(f"Could not load or create project '{CANARY_PROJECT_NAME}'")
            
        # STRICT PRECONDITION CHECK: Current project MUST be CANARY_PROJECT_NAME
        current_project = pm.GetCurrentProject()
        current_name = current_project.GetName()
        if current_name != CANARY_PROJECT_NAME:
            raise RuntimeError(f"SAFETY ABORT: Active project is '{current_name}', expected '{CANARY_PROJECT_NAME}'! Never modify '{current_name}'!")
            
        log_event(events, "target_canary_project", "PASS", {"active_project": current_name})
    except Exception as e:
        err = f"Project targeting failed: {e}"
        log_event(events, "target_canary_project", "FAILED", {"error": err})
        summary["error"] = err
        return summary, events

    # Step 4: Import Media into MediaPool
    try:
        mp = current_project.GetMediaPool()
        if not mp:
            raise RuntimeError("GetMediaPool returned None")
            
        root_folder = mp.GetRootFolder()
        existing_clips = root_folder.GetClipList() or []
        target_clip = None
        
        # Check if test clip already imported
        for clip in existing_clips:
            if clip.GetName() == Path(TEST_MEDIA_PATH).name:
                target_clip = clip
                break
                
        if target_clip:
            log_event(events, "media_pool_reuse", "PASS", {"clip_name": target_clip.GetName()})
        else:
            print(f"Importing test media: {TEST_MEDIA_PATH}...")
            imported = mp.ImportMedia([TEST_MEDIA_PATH])
            summary["operations_tested"].append("mp.ImportMedia")
            if not imported or len(imported) == 0:
                raise RuntimeError("mp.ImportMedia returned no clips")
            target_clip = imported[0]
            log_event(events, "media_pool_import", "PASS", {"clip_name": target_clip.GetName()})
            
    except Exception as e:
        err = f"Media import failed: {e}"
        log_event(events, "media_pool_import", "FAILED", {"error": err})
        summary["error"] = err
        return summary, events

    # Step 5: Create Timeline
    try:
        # Check if timeline already exists
        existing_tl_count = current_project.GetTimelineCount()
        timeline = None
        for i in range(1, int(existing_tl_count) + 1):
            tl_candidate = current_project.GetTimelineByIndex(i)
            if tl_candidate and tl_candidate.GetName() == TIMELINE_NAME:
                timeline = tl_candidate
                break
                
        if timeline:
            log_event(events, "timeline_reuse", "PASS", {"timeline_name": TIMELINE_NAME})
        else:
            print(f"Creating empty timeline '{TIMELINE_NAME}'...")
            timeline = mp.CreateEmptyTimeline(TIMELINE_NAME)
            summary["operations_tested"].append("mp.CreateEmptyTimeline")
            if not timeline:
                raise RuntimeError(f"mp.CreateEmptyTimeline('{TIMELINE_NAME}') returned None/False")
            log_event(events, "timeline_create", "PASS", {"timeline_name": TIMELINE_NAME})
            
        current_project.SetCurrentTimeline(timeline)
        summary["operations_tested"].append("project.SetCurrentTimeline")
        log_event(events, "set_current_timeline", "PASS", {"timeline_name": timeline.GetName()})
    except Exception as e:
        err = f"Timeline creation failed: {e}"
        log_event(events, "timeline_create", "FAILED", {"error": err})
        summary["error"] = err
        return summary, events

    # Step 6: Place Media Pool Clip on Timeline (AppendToTimeline)
    try:
        existing_items = timeline.GetItemListInTrack("video", 1) or []
        if len(existing_items) > 0:
            print(f"Timeline already has {len(existing_items)} item(s) on video track 1.")
            placed_item = existing_items[0]
            log_event(events, "clip_placement_reuse", "PASS", {"existing_count": len(existing_items)})
        else:
            print("Placing clip on video track 1 (72 frames = 3.0s @ 24fps)...")
            clip_plan = [{
                "mediaPoolItem": target_clip,
                "startFrame": 0,
                "endFrame": 72
            }]
            appended = mp.AppendToTimeline(clip_plan)
            summary["operations_tested"].append("mp.AppendToTimeline")
            if not appended:
                raise RuntimeError("mp.AppendToTimeline returned None or empty list")
            log_event(events, "clip_placement", "PASS", {"appended": len(appended) if isinstance(appended, list) else bool(appended)})

    except Exception as e:
        err = f"Clip placement failed: {e}"
        log_event(events, "clip_placement", "FAILED", {"error": err})
        summary["error"] = err
        return summary, events

    # Step 7: Fresh Read-Only Query Verification
    try:
        print("Performing fresh read-only verification query...")
        fresh_items = timeline.GetItemListInTrack("video", 1) or []
        if not fresh_items:
            raise RuntimeError("Verification failed: video track 1 has 0 items after edit!")
            
        item = fresh_items[0]
        item_name = item.GetName()
        item_start = item.GetStart()
        item_end = item.GetEnd()
        item_duration = item.GetDuration()
        
        mp_item = item.GetMediaPoolItem()
        mp_item_name = mp_item.GetName() if mp_item else None
        
        verification_data = {
            "verified": True,
            "project_name": current_project.GetName(),
            "timeline_name": timeline.GetName(),
            "track_type": "video",
            "track_index": 1,
            "clip_name": item_name,
            "media_pool_source": mp_item_name,
            "start_frame": item_start,
            "end_frame": item_end,
            "duration_frames": item_duration,
            "total_items_on_track": len(fresh_items)
        }
        
        summary["timeline_verification"] = verification_data
        log_event(events, "fresh_query_verification", "PASS", verification_data)
        
        # Step 8: Save Canary Project
        pm.SaveProject()
        summary["operations_tested"].append("pm.SaveProject")
        log_event(events, "save_canary_project", "PASS", {"project": CANARY_PROJECT_NAME})
        
        summary["status"] = "ALL_CHECKS_PASSED"
        
    except Exception as e:
        err = f"Verification query failed: {e}"
        log_event(events, "fresh_query_verification", "FAILED", {"error": err})
        summary["error"] = err
        return summary, events

    return summary, events

if __name__ == "__main__":
    result, event_log = run_canary_edit()
    print("\n" + "=" * 70)
    print("FINAL SUMMARY:")
    print(json.dumps(result, indent=2))
    print("=" * 70)
    
    # Save raw result
    out_path = Path(__file__).resolve().parent / "test-results" / "first_edit_canary_raw.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": result, "events": event_log}, f, indent=2)
    print(f"Raw results written to: {out_path}")
