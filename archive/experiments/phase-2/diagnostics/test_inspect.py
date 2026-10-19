"""
Test Read-Only Inspection of DaVinci Resolve Project Library
"""
import os
import sqlite3
import json

def inspect_local_project(project_name="chaitu"):
    appdata = os.environ.get("APPDATA")
    db_path = os.path.join(
        appdata,
        "Blackmagic Design",
        "DaVinci Resolve",
        "Support",
        "Resolve Project Library",
        "Resolve Projects",
        "Users",
        "guest",
        "Projects",
        project_name,
        "Project.db"
    )
    
    if not os.path.exists(db_path):
        return {"error": f"Project db not found at {db_path}"}
        
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    # Project info
    cur.execute("SELECT SM_Project_id, ProjectName, ProjectVersion, NumTotalStreams, CurrentTimelineIndex FROM SM_Project;")
    proj_row = cur.fetchone()
    project_info = {
        "project_id": proj_row[0],
        "project_name": proj_row[1] if proj_row[1] else project_name,
        "project_version": proj_row[2],
        "streams": proj_row[3],
        "current_timeline_index": proj_row[4],
    }
    
    # Timelines
    cur.execute("SELECT Sm2Timeline_id, Name, ModTimeInSecs, CreateTimeInSecs FROM Sm2Timeline;")
    timelines = []
    for r in cur.fetchall():
        timelines.append({
            "timeline_id": r[0],
            "timeline_name": r[1],
            "modified_time_s": r[2],
            "created_time_s": r[3],
        })
        
    # Timeline Items / Clips
    cur.execute('SELECT Name, Start, Duration, "In", MediaFilePath, MediaFrameRate FROM Sm2TiItem;')
    timeline_items = []
    for r in cur.fetchall():
        path_val = r[4]
        if isinstance(path_val, bytes):
            try:
                path_val = path_val.decode('utf-8', errors='ignore')
            except Exception:
                path_val = str(path_val)
        timeline_items.append({
            "name": r[0],
            "start_frame": r[1],
            "duration_frames": r[2],
            "in_frame": r[3],
            "media_file_path": path_val,
            "frame_rate": r[5]
        })
        
    # Media Pool items
    cur.execute("SELECT Sm2MpMedia_id, Name, DbType FROM Sm2MpMedia;")
    media_items = []
    for r in cur.fetchall():
        media_items.append({
            "media_id": r[0],
            "name": r[1],
            "type": r[2],
        })
        
    # Non-empty table counts
    cur.execute("SELECT tbl_name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cur.fetchall()]
    table_counts = {}
    for t in tables:
        try:
            cur.execute(f'SELECT count(*) FROM "{t}";')
            cnt = cur.fetchone()[0]
            if cnt > 0:
                table_counts[t] = cnt
        except Exception:
            pass
            
    conn.close()
    
    return {
        "status": "success",
        "access_mode": "read_only_sqlite",
        "db_path": db_path,
        "project": project_info,
        "timelines": timelines,
        "timeline_items": timeline_items,
        "media_pool": media_items,
        "active_tables": table_counts,
    }

if __name__ == "__main__":
    res = inspect_local_project("chaitu")
    print(json.dumps(res, indent=2, default=lambda x: x.decode('utf-8', errors='ignore') if isinstance(x, bytes) else str(x)))
