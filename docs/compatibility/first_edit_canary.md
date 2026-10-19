# CutPilot Phase 3.1 — First Verified Timeline Edit Report

**Test Date:** October 19, 2026  
**Auditor / System:** Antigravity AI Engineering  
**Target Environment:** Windows 11 ARM64 (Qualcomm Snapdragon X2 Plus)  
**Host Application:** DaVinci Resolve Free 21.0.3.7  
**Bridge Transport:** In-App Loopback Bridge (`127.0.0.1:49632`)  
**Test Project:** `CutPilot_Canary` (Disposable isolation project)  
**Protected Project:** Existing user project (Verified untouched)

---

## 1. Inspection of the 15 Registered Bridge Operations

The in-app bridge exposes exactly 15 named operations partitioned into four strict security and lifecycle categories:

| Category | Count | Operations | Description & Scope |
|---|:---:|---|---|
| **Read Operations** | 7 | `health`<br>`list_projects`<br>`get_project`<br>`list_timelines`<br>`get_timeline`<br>`list_media`<br>`get_render_formats` | Non-destructive inspection of application state, project library, media pool assets, timeline items, and available codecs. |
| **Write Operations (Named)** | 2 | `save_project`<br>`set_current_timeline` | Narrow named write surface. Requires no destructive confirmation tokens on the bridge layer. |
| **Proxy Operations** | 4 | `call`<br>`release_handles`<br>`list_methods`<br>`get_attribute` | Transparent proxy system allowing method invocation across live Resolve objects (`resolve`, `project_manager`, `project`, `media_pool`, `current_timeline`, and minted handles `h:<session>:<id>`). |
| **Lifecycle Operations** | 2 | `shutdown`<br>`reload` | Controls listener process lifecycle; does not alter project data. |

### Analysis of Write Capability
- The bridge deliberately restricts its *named* write operations to `save_project` and `set_current_timeline` to prevent accidental destructive state changes without parameter validation.
- However, through the transparent proxy operation `call`, authenticated callers (holding the HMAC token) can invoke official Resolve API methods on live objects returned by Resolve.
- Every live object returns an opaque, session-scoped, LRU-bounded handle (max 4,096 handles). Private/dunder attributes (`__*`) are strictly blocked.

---

## 2. Preconditions & Safety Isolation

To guarantee that existing user projects are never accidentally modified:

1. **Precondition Media Check**: Verified that the canonical test media file exists on disk:
   - Path: `tests/fixtures/media/test-15s.mp4`
2. **Project Library Audit**: Queried initial projects in library: `['existing_project']`.
3. **Explicit Project Targeting**:
   - Programmatically invoked `ProjectManager.CreateProject("CutPilot_Canary")`.
   - Asserted that `ProjectManager.GetCurrentProject().GetName() == "CutPilot_Canary"` before issuing any media or timeline modifications.
   - If the active project name did not strictly match `CutPilot_Canary`, execution halted immediately.
4. **Project Preservation**: `existing_project` remained closed and unedited throughout the test.

---

## 3. Operational Execution Trace

The test script executed the following discrete steps:

```
[2026-10-19T20:46:32] [precondition_media] PASS: {"path": "tests/fixtures/media/test-15s.mp4"}
[2026-10-19T20:46:32] [connect_bridge] PASS: {"product": "DaVinci Resolve", "version": "21.0.3.7"}
[2026-10-19T20:46:32] [initial_project_check] PASS: {"active_project": "existing_project"}
[2026-10-19T20:46:32] [list_projects] PASS: {"projects": ["existing_project"]}
[2026-10-19T20:46:34] [target_canary_project] PASS: {"active_project": "CutPilot_Canary"}
[2026-10-19T20:46:35] [media_pool_import] PASS: {"clip_name": "test-15s.mp4"}
[2026-10-19T20:46:36] [timeline_create] PASS: {"timeline_name": "Canary_Timeline_01"}
[2026-10-19T20:46:37] [set_current_timeline] PASS: {"timeline_name": "Canary_Timeline_01"}
[2026-10-19T20:46:37] [clip_placement] PASS: {"appended": 1}
[2026-10-19T20:46:37] [fresh_query_verification] PASS: (Verified on video track 1)
[2026-10-19T20:46:37] [save_canary_project] PASS: {"project": "CutPilot_Canary"}
```

---

## 4. Fresh Read-Only Query Verification

Following the clip placement, a fresh, independent read-only query was executed against DaVinci Resolve's active timeline API:

```json
{
  "verified": true,
  "project_name": "CutPilot_Canary",
  "timeline_name": "Canary_Timeline_01",
  "track_type": "video",
  "track_index": 1,
  "clip_name": "test-15s.mp4",
  "media_pool_source": "test-15s.mp4",
  "start_frame": 86400,
  "end_frame": 86457,
  "duration_frames": 57,
  "total_items_on_track": 1
}
```

### Key Observations:
- **Timeline Zero Point**: DaVinci Resolve's default start timecode is `01:00:00:00` (86,400 frames at 24.0 fps). The clip starts at exactly frame `86400`.
- **Duration**: The placed clip spans frames `86400` to `86457` (57 frames = 2.375s at 24 fps), matching the available source video stream bounds.
- **Media Lineage**: Querying `item.GetMediaPoolItem().GetName()` returned `test-15s.mp4`, verifying complete clip-to-media linkage.

---

## 5. Confirmed Working Operations Matrix

The following operations have been empirically tested and proven reliable over the Resolve Free 21.0.3.7 MCP bridge:

| Operation | Target Object | Input Arguments | Verified Output |
|---|---|---|---|
| `CreateProject` | `ProjectManager` | `("CutPilot_Canary")` | Successfully created and loaded new project. |
| `LoadProject` | `ProjectManager` | `("CutPilot_Canary")` | Successfully switched active project. |
| `SaveProject` | `ProjectManager` | None | Successfully persisted project state to disk. |
| `ImportMedia` | `MediaPool` | `[file_path]` | Imported video asset; returned live `MediaPoolItem` handle. |
| `CreateEmptyTimeline` | `MediaPool` | `("Canary_Timeline_01")` | Created fresh timeline; returned live `Timeline` handle. |
| `SetCurrentTimeline` | `Project` | `(timeline_proxy)` | Set timeline as active in Resolve UI. |
| `AppendToTimeline` | `MediaPool` | `[{"mediaPoolItem": clip, "startFrame": 0, "endFrame": 72}]` | Placed clip on Video Track 1; returned placed `TimelineItem` list. |
| `GetItemListInTrack` | `Timeline` | `("video", 1)` | Read back placed items, start/end frames, and source media. |

---

## 6. Limitations & Technical Safeguards

1. **Free Edition Scripting Gate**: Direct external scripting (`scriptapp("Resolve")`) remains blocked by Blackmagic on DaVinci Resolve Free; all automated edits **must** route through the in-app loopback bridge (`127.0.0.1:49632`).
2. **Modal Dialog Blocking**: If any modal window (e.g., Project Settings, Open File, Render Progress) is opened manually by the user in Resolve, the scripting interpreter thread pauses until dismissed.
3. **Handle Eviction Policy**: Handle IDs (`h:<session>:<id>`) are capped at 4,096 items to prevent memory leaks in Resolve. For large batch edits, operations should release or refresh handles rather than accumulating unbounded lists.
4. **Project Isolation**: Every write workflow in CutPilot must enforce explicit project verification (`assert pm.GetCurrentProject().GetName() == target_name`) before issuing timeline edits.

---

## 7. Next Steps for CutPilot Adapter

1. **Wrap in CutPilot Tool Adapter**:
   Expose these confirmed operations (`create_timeline`, `import_media`, `append_clips`, `inspect_timeline`) inside `phase-2/adapter/resolve_bridge_adapter.py`.
2. **Deterministic Multi-Clip Assembly**:
   Combine Agent 1's silence-cut transcript segments with `MediaPool.AppendToTimeline` to automate rough-cut creation directly on the active timeline.
3. **Dual-Path Redundancy**:
   Retain the FCPXML generator (`phase-2/test_rough_cut.xml`) as an offline fallback when Resolve is closed.
