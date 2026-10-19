"""
CutPilot - Resolve MCP Bridge Read-Only Query Verification Script
"""
import sys
import os
import json
from pathlib import Path

# Add davinci-resolve-mcp to path
MCP_REPO = Path(__file__).resolve().parent / "reference" / "davinci-resolve-mcp"
sys.path.insert(0, str(MCP_REPO))

from src.utils import resolve_bridge_client

def test_bridge_query():
    print("Testing connection to in-app bridge at 127.0.0.1:49632...")
    try:
        resolve = resolve_bridge_client.connect(require_enabled=False, timeout=5.0)
        print("Connected successfully to Resolve Bridge Proxy!")
        
        product_name = resolve.GetProductName()
        version = resolve.GetVersionString()
        print(f"Resolve Product: {product_name} {version}")
        
        pm = resolve.GetProjectManager()
        current_project = pm.GetCurrentProject()
        
        if current_project:
            proj_name = current_project.GetName()
            timeline_count = current_project.GetTimelineCount()
            print(f"Current Project: '{proj_name}'")
            print(f"Timeline Count: {timeline_count}")
            
            # Read-only query: list timelines
            timelines = []
            for i in range(1, int(timeline_count) + 1):
                tl = current_project.GetTimelineByIndex(i)
                if tl:
                    timelines.append({
                        "index": i,
                        "name": tl.GetName(),
                        "track_count_video": tl.GetTrackCount("video"),
                        "track_count_audio": tl.GetTrackCount("audio"),
                    })
            print("Timelines:", json.dumps(timelines, indent=2))
            
            return {
                "status": "PASS",
                "product": product_name,
                "version": version,
                "project": proj_name,
                "timelines": timelines,
            }
        else:
            print("No project is currently open in Resolve.")
            return {
                "status": "PASS_NO_PROJECT_OPEN",
                "product": product_name,
                "version": version,
            }
            
    except resolve_bridge_client.BridgeUnavailable as e:
        print(f"Bridge unavailable: {e}")
        return {"status": "UNAVAILABLE", "error": str(e)}
    except Exception as e:
        print(f"Query error: {e}")
        return {"status": "ERROR", "error": str(e)}

if __name__ == "__main__":
    res = test_bridge_query()
    print("Result:", res)
