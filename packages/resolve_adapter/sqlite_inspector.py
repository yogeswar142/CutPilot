"""
CutPilot SQLite Project Inspector
Provides safe, read-only inspection of DaVinci Resolve Project Libraries via direct SQLite connections (mode=ro).
Zero dependencies on external DaVinci Resolve scripting processes.
"""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

class SqliteInspector:
    """Safely inspects local DaVinci Resolve Project.db files in read-only mode."""

    DEFAULT_LIBRARY_PATH = (
        Path(os.environ.get("APPDATA", ""))
        / "Blackmagic Design"
        / "DaVinci Resolve"
        / "Support"
        / "Resolve Project Library"
        / "Resolve Projects"
        / "Users"
        / "guest"
        / "Projects"
    )

    def __init__(self, projects_root: Optional[Path] = None):
        self.projects_root = Path(projects_root) if projects_root else self.DEFAULT_LIBRARY_PATH

    def list_projects(self) -> List[str]:
        """Lists all local project names found in the project library."""
        if not self.projects_root.is_dir():
            return []
        projects = []
        for p in self.projects_root.iterdir():
            if p.is_dir() and (p / "Project.db").is_file():
                projects.append(p.name)
        return sorted(projects)

    def _connect_ro(self, project_name: str) -> sqlite3.Connection:
        db_path = self.projects_root / project_name / "Project.db"
        if not db_path.is_file():
            raise FileNotFoundError(f"Resolve Project.db not found for project '{project_name}' at {db_path}")
        uri = f"file:{db_path.as_posix()}?mode=ro"
        return sqlite3.connect(uri, uri=True)

    def inspect_project(self, project_name: str) -> Dict[str, Any]:
        """Inspects project metadata, version, and defined timelines."""
        if not project_name:
            raise ValueError("project_name must be specified for SQLite inspection")
        conn = self._connect_ro(project_name)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT SM_Project_id, ProjectName, ProjectVersion, NumTotalStreams, CurrentTimelineIndex FROM SM_Project;"
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"No SM_Project record in {project_name}/Project.db")

            project_meta = {
                "project_id": row[0],
                "project_name": row[1] if row[1] else project_name,
                "project_version": row[2],
                "streams": row[3],
                "current_timeline_index": row[4],
            }

            cur.execute("SELECT Sm2Timeline_id, Name, ModTimeInSecs, CreateTimeInSecs FROM Sm2Timeline;")
            timelines = []
            for r in cur.fetchall():
                timelines.append({
                    "timeline_id": r[0],
                    "timeline_name": r[1],
                    "modified_at_timestamp": r[2],
                    "created_at_timestamp": r[3],
                })

            return {
                "status": "success",
                "project": project_meta,
                "timelines": timelines,
            }
        finally:
            conn.close()

    def inspect_media(self, project_name: str) -> Dict[str, Any]:
        """Inspects media pool clips, timeline placements, and source file paths."""
        if not project_name:
            raise ValueError("project_name must be specified for SQLite inspection")
        conn = self._connect_ro(project_name)
        try:
            cur = conn.cursor()

            # Media pool items
            cur.execute("SELECT Sm2MpMedia_id, Name, DbType FROM Sm2MpMedia;")
            media_items = []
            for r in cur.fetchall():
                media_items.append({
                    "media_id": r[0],
                    "name": r[1],
                    "type": r[2],
                })

            # Timeline clip placements
            cur.execute('SELECT Name, Start, Duration, "In", MediaFilePath, MediaFrameRate FROM Sm2TiItem;')
            timeline_items = []
            for r in cur.fetchall():
                path_val = r[4]
                if isinstance(path_val, bytes):
                    path_val = path_val.decode("utf-8", errors="ignore")
                timeline_items.append({
                    "name": r[0],
                    "start_frame": int(r[1]) if r[1] is not None and str(r[1]).isdigit() else r[1],
                    "duration_frames": int(r[2]) if r[2] is not None and str(r[2]).isdigit() else r[2],
                    "in_frame": int(r[3]) if r[3] is not None and str(r[3]).isdigit() else r[3],
                    "source_path": path_val,
                })

            return {
                "status": "success",
                "media_pool": media_items,
                "timeline_items": timeline_items,
            }
        finally:
            conn.close()
