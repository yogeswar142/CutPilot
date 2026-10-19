"""
CutPilot - Quick Bridge Verification Script
Checks bridge connection to DaVinci Resolve on 127.0.0.1:49632 and queries current project.
"""
import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.resolve_adapter.adapter import ResolveBridgeAdapter
from packages.resolve_adapter.bridge_client import BridgeUnavailable

def main():
    print("Connecting to DaVinci Resolve in-app bridge at 127.0.0.1:49632...")
    adapter = ResolveBridgeAdapter(timeout=5.0)
    try:
        proj_name = adapter.get_current_project_name()
        projects = adapter.list_projects()
        print(f"[PASS] Connected successfully!")
        print(f"Active Project: '{proj_name}'")
        print(f"Projects in Library: {projects}")
        
        curr = adapter.get_current_project()
        if curr:
            tl_count = curr.GetTimelineCount() or 0
            print(f"Timeline Count in '{proj_name}': {tl_count}")
            for i in range(1, int(tl_count) + 1):
                tl = curr.GetTimelineByIndex(i)
                if tl:
                    print(f"  [{i}] {tl.GetName()} (Video tracks: {tl.GetTrackCount('video')}, Audio: {tl.GetTrackCount('audio')})")
    except BridgeUnavailable as e:
        print(f"[UNAVAILABLE] Could not reach bridge: {e}")
        print("Hint: Launch Resolve using scripts/launch_resolve.bat and click Workspace > Scripts > resolve_bridge.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Bridge query failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
