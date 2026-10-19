"""
CutPilot Resolve Bridge Adapter
High-level, deterministic editing interface wrapping the in-app Resolve bridge.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from packages.core.models import TimelineVerificationResult
from packages.resolve_adapter.bridge_client import connect_resolve, BridgeProxy, BridgeUnavailable, BridgeCallError
from packages.resolve_adapter.framerate import convert_frame_bounds

class ResolveBridgeAdapter:
    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout
        self._resolve: Optional[BridgeProxy] = None

    @property
    def resolve(self) -> BridgeProxy:
        if self._resolve is None:
            self._resolve = connect_resolve(timeout=self.timeout)
        return self._resolve

    @property
    def project_manager(self) -> Any:
        return self.resolve.GetProjectManager()

    def get_current_project(self) -> Optional[Any]:
        return self.project_manager.GetCurrentProject()

    def get_current_project_name(self) -> Optional[str]:
        proj = self.get_current_project()
        return proj.GetName() if proj else None

    def list_projects(self) -> List[str]:
        return self.project_manager.GetProjectListInCurrentFolder() or []

    def create_project(self, name: str) -> bool:
        res = self.project_manager.CreateProject(name)
        return res is not None and res is not False

    def load_project(self, name: str) -> bool:
        res = self.project_manager.LoadProject(name)
        return res is not None and res is not False

    def save_project(self) -> bool:
        return bool(self.project_manager.SaveProject())

    def get_media_pool(self) -> Any:
        proj = self.get_current_project()
        if not proj:
            raise RuntimeError("No project is currently open in Resolve.")
        return proj.GetMediaPool()

    def import_media(self, file_path: str) -> Any:
        path = str(Path(file_path).resolve())
        mp = self.get_media_pool()
        root = mp.GetRootFolder()

        # Check existing
        for clip in (root.GetClipList() or []):
            props = clip.GetClipProperty() or {}
            if props.get("File Path") == path or clip.GetName() == Path(path).name:
                return clip

        imported = mp.ImportMedia([path])
        if not imported or len(imported) == 0:
            raise RuntimeError(f"MediaPool.ImportMedia failed for: {path}")
        return imported[0]

    def ensure_timeline(self, name: str, fps: float = 24.0) -> Any:
        proj = self.get_current_project()
        if not proj:
            raise RuntimeError("No project is currently open in Resolve.")

        count = proj.GetTimelineCount() or 0
        for i in range(1, int(count) + 1):
            tl = proj.GetTimelineByIndex(i)
            if tl and tl.GetName() == name:
                proj.SetCurrentTimeline(tl)
                return tl

        mp = proj.GetMediaPool()
        tl = mp.CreateEmptyTimeline(name)
        if not tl:
            raise RuntimeError(f"Failed to create timeline: '{name}'")
        proj.SetCurrentTimeline(tl)
        return tl

    def append_clip(
        self,
        clip: Any,
        start_frame: int,
        end_frame: int,
        track_type: str = "video",
        track_index: int = 1,
    ) -> Any:
        """
        Appends a slice of a media pool item to the current timeline.
        """
        mp = self.get_media_pool()
        clip_plan = [{
            "mediaPoolItem": clip,
            "startFrame": int(start_frame),
            "endFrame": int(end_frame)
        }]
        appended = mp.AppendToTimeline(clip_plan)
        if not appended:
            raise RuntimeError(f"AppendToTimeline failed for frames [{start_frame}:{end_frame}]")
        return appended

    def verify_timeline(self, timeline_name: str, track_type: str = "video", track_index: int = 1) -> TimelineVerificationResult:
        proj = self.get_current_project()
        if not proj:
            return TimelineVerificationResult(
                verified=False, project_name="", timeline_name=timeline_name,
                track_type=track_type, track_index=track_index, clip_name="",
                media_pool_source=None, start_frame=0, end_frame=0, duration_frames=0,
                total_items_on_track=0, errors=["No project currently open."]
            )

        tl = proj.GetCurrentTimeline()
        if not tl or tl.GetName() != timeline_name:
            # Try to find by name
            count = proj.GetTimelineCount() or 0
            for i in range(1, int(count) + 1):
                c = proj.GetTimelineByIndex(i)
                if c and c.GetName() == timeline_name:
                    tl = c
                    break

        if not tl:
            return TimelineVerificationResult(
                verified=False, project_name=proj.GetName(), timeline_name=timeline_name,
                track_type=track_type, track_index=track_index, clip_name="",
                media_pool_source=None, start_frame=0, end_frame=0, duration_frames=0,
                total_items_on_track=0, errors=[f"Timeline '{timeline_name}' not found."]
            )

        items = tl.GetItemListInTrack(track_type, track_index) or []
        if not items:
            return TimelineVerificationResult(
                verified=False, project_name=proj.GetName(), timeline_name=timeline_name,
                track_type=track_type, track_index=track_index, clip_name="",
                media_pool_source=None, start_frame=0, end_frame=0, duration_frames=0,
                total_items_on_track=0, errors=[f"Track {track_type} {track_index} is empty."]
            )

        first = items[0]
        mp_item = first.GetMediaPoolItem()
        mp_name = mp_item.GetName() if mp_item else None

        return TimelineVerificationResult(
            verified=True,
            project_name=proj.GetName(),
            timeline_name=tl.GetName(),
            track_type=track_type,
            track_index=track_index,
            clip_name=first.GetName(),
            media_pool_source=mp_name,
            start_frame=first.GetStart(),
            end_frame=first.GetEnd(),
            duration_frames=first.GetDuration(),
            total_items_on_track=len(items)
        )
