"""
CutPilot Resolve Adapter Package
DaVinci Resolve in-app bridge client, high-level adapter, framerate management, and SQLite inspector.
"""
from packages.resolve_adapter.bridge_client import connect_resolve, BridgeUnavailable, BridgeCallError
from packages.resolve_adapter.adapter import ResolveBridgeAdapter
from packages.resolve_adapter.framerate import convert_frame_bounds, seconds_to_frames, frames_to_seconds
from packages.resolve_adapter.sqlite_inspector import SqliteInspector

__all__ = [
    "connect_resolve",
    "BridgeUnavailable",
    "BridgeCallError",
    "ResolveBridgeAdapter",
    "convert_frame_bounds",
    "seconds_to_frames",
    "frames_to_seconds",
    "SqliteInspector",
]
