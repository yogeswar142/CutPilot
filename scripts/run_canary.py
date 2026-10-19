"""
CutPilot - Run Canary Workflow
Executes the safe, reversible canary timeline edit on DaVinci Resolve.
"""
import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.resolve_adapter.adapter import ResolveBridgeAdapter
from packages.core.config import settings

def main():
    print("=" * 70)
    print("CutPilot Canary Workflow Runner")
    print("=" * 70)

    adapter = ResolveBridgeAdapter(timeout=5.0)
    canary_project = "CutPilot_Canary"
    timeline_name = "Canary_Timeline_01"

    # Precondition: verify bridge connection
    try:
        active = adapter.get_current_project_name()
        print(f"Connected to Resolve bridge! Initial active project: '{active}'")
    except Exception as e:
        print(f"[FAIL] Could not connect to Resolve bridge: {e}")
        print("Please launch Resolve using scripts/launch_resolve.bat and run Workspace > Scripts > resolve_bridge.")
        sys.exit(1)

    # Precondition: target canary project safely
    projects = adapter.list_projects()
    if canary_project in projects:
        print(f"Loading existing project '{canary_project}'...")
        adapter.load_project(canary_project)
    else:
        print(f"Creating project '{canary_project}'...")
        adapter.create_project(canary_project)

    active = adapter.get_current_project_name()
    if active != canary_project:
        print(f"[SAFETY ABORT] Active project is '{active}', expected '{canary_project}'!")
        sys.exit(1)

    # Import canonical test media
    test_media = str(settings.canonical_test_media)
    print(f"Importing test media: {test_media}...")
    clip = adapter.import_media(test_media)
    print(f"Media Pool clip ready: '{clip.GetName()}'")

    # Ensure timeline
    print(f"Ensuring timeline '{timeline_name}'...")
    tl = adapter.ensure_timeline(timeline_name, fps=24.0)

    # Append clip (0 to 72 frames)
    print("Placing 72-frame slice on video track 1...")
    adapter.append_clip(clip, start_frame=0, end_frame=72, track_type="video", track_index=1)

    # Save
    adapter.save_project()
    print("Project saved.")

    # Readback verification
    print("Running readback query...")
    ver = adapter.verify_timeline(timeline_name, "video", 1)
    print("Verification result:")
    print(json.dumps(ver.to_dict(), indent=2))

    if ver.verified:
        print("\n[SUCCESS] Canary workflow completed and verified!")
    else:
        print("\n[FAILED] Verification did not pass!")
        sys.exit(1)

if __name__ == "__main__":
    main()
