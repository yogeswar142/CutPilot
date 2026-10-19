"""
Integration Test: CutPilot Canary Timeline Edit
Tests the complete editing workflow over the in-app Resolve bridge.
"""
import pytest
from pathlib import Path
from packages.resolve_adapter.adapter import ResolveBridgeAdapter
from packages.core.config import settings

@pytest.mark.live
def test_live_canary_edit_workflow():
    adapter = ResolveBridgeAdapter(timeout=5.0)
    
    # 1. Check bridge connection
    try:
        active = adapter.get_current_project_name()
    except Exception as e:
        pytest.skip(f"DaVinci Resolve bridge not running on 127.0.0.1:49632: {e}")

    # 2. Assert/Target Canary Project
    projects = adapter.list_projects()
    canary_project = "CutPilot_Canary"
    
    if canary_project in projects:
        adapter.load_project(canary_project)
    else:
        adapter.create_project(canary_project)
        
    assert adapter.get_current_project_name() == canary_project

    # 3. Import canonical test media
    test_media = str(settings.canonical_test_media)
    clip = adapter.import_media(test_media)
    assert clip is not None
    assert clip.GetName() == "test-15s.mp4"

    # 4. Ensure timeline
    tl = adapter.ensure_timeline("Canary_Timeline_01", fps=24.0)
    assert tl is not None
    assert tl.GetName() == "Canary_Timeline_01"

    # 5. Verify timeline item
    ver = adapter.verify_timeline("Canary_Timeline_01", "video", 1)
    assert ver.verified is True
    assert ver.clip_name == "test-15s.mp4"
    assert ver.total_items_on_track >= 1
    assert ver.duration_frames > 0

    # 6. Save project
    saved = adapter.save_project()
    assert saved is True
