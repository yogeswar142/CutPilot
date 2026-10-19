"""
CutPilot Canonical MCP Server (cutpilot-mcp)
Exposes verified, deterministic DaVinci Resolve editing tools via Model Context Protocol JSON-RPC stdio.
Zero external framework dependencies.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from packages.resolve_adapter.adapter import ResolveBridgeAdapter
from packages.resolve_adapter.sqlite_inspector import SqliteInspector
from packages.editing.captions import CaptionsGenerator, generate_srt, generate_vtt
from packages.editing.fcpxml import CutPlan, PartSource, ClipSegment, FcpXmlGenerator
from packages.media.inspector import inspect_media

SERVER_NAME = "cutpilot-mcp"
SERVER_VERSION = "1.0.0"

class CutPilotMcpServer:
    def __init__(self) -> None:
        self.adapter = ResolveBridgeAdapter()
        self.sqlite = SqliteInspector()
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._register_tools()

    def _register_tools(self) -> None:
        self.tools["cutpilot_inspect_project"] = {
            "name": "cutpilot_inspect_project",
            "description": "Inspects active DaVinci Resolve project metadata, timeline counts, and media pool contents.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Optional project name to inspect. Defaults to active project in Resolve."
                    }
                }
            },
            "handler": self._tool_inspect_project
        }

        self.tools["cutpilot_inspect_timeline"] = {
            "name": "cutpilot_inspect_timeline",
            "description": "Inspects clip placements, start frames, and durations on a specific timeline track.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "timeline_name": {"type": "string", "description": "Target timeline name."},
                    "track_type": {"type": "string", "enum": ["video", "audio"], "default": "video"},
                    "track_index": {"type": "integer", "default": 1}
                },
                "required": ["timeline_name"]
            },
            "handler": self._tool_inspect_timeline
        }

        self.tools["cutpilot_create_project"] = {
            "name": "cutpilot_create_project",
            "description": "Safely creates a new project or opens an existing one. Never modifies unconfirmed projects.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Name of project to create or load."}
                },
                "required": ["project_name"]
            },
            "handler": self._tool_create_project
        }

        self.tools["cutpilot_import_media"] = {
            "name": "cutpilot_import_media",
            "description": "Imports a verified local media file into the active project Media Pool.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to media file."}
                },
                "required": ["file_path"]
            },
            "handler": self._tool_import_media
        }

        self.tools["cutpilot_create_timeline"] = {
            "name": "cutpilot_create_timeline",
            "description": "Creates a new empty timeline in the active project with explicit frame rate.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "timeline_name": {"type": "string", "description": "Name for the new timeline."},
                    "fps": {"type": "number", "default": 24.0, "description": "Timeline framerate (e.g. 24.0, 30.0)."}
                },
                "required": ["timeline_name"]
            },
            "handler": self._tool_create_timeline
        }

        self.tools["cutpilot_place_clip"] = {
            "name": "cutpilot_place_clip",
            "description": "Appends a frame-accurate clip slice onto a timeline track.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path or name of source media clip in pool."},
                    "start_frame": {"type": "integer", "description": "Source in frame (>= 0)."},
                    "end_frame": {"type": "integer", "description": "Source out frame (> start_frame)."},
                    "track_type": {"type": "string", "enum": ["video", "audio"], "default": "video"},
                    "track_index": {"type": "integer", "default": 1}
                },
                "required": ["file_path", "start_frame", "end_frame"]
            },
            "handler": self._tool_place_clip
        }

        self.tools["cutpilot_generate_captions"] = {
            "name": "cutpilot_generate_captions",
            "description": "Generates synchronized .srt or .vtt subtitle file from word-level transcripts.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "words": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of word objects with 'word', 'start', 'end'."
                    },
                    "output_path": {"type": "string", "description": "Path to write .srt or .vtt file."},
                    "format": {"type": "string", "enum": ["srt", "vtt"], "default": "srt"}
                },
                "required": ["words", "output_path"]
            },
            "handler": self._tool_generate_captions
        }

        fcp7_schema = {
            "type": "object",
            "properties": {
                "plan": {"type": "object", "description": "CutPlan object with parts and segments."},
                "output_path": {"type": "string", "description": "Path to write .xml file."}
            },
            "required": ["plan", "output_path"]
        }

        self.tools["cutpilot_export_fcp7xml"] = {
            "name": "cutpilot_export_fcp7xml",
            "description": "Exports an Apple Final Cut Pro 7 XML (xmeml v4) timeline file compatible with DaVinci Resolve and Premiere Pro.",
            "inputSchema": fcp7_schema,
            "handler": self._tool_export_fcpxml
        }

        # Backwards compatibility alias
        self.tools["cutpilot_export_fcpxml"] = {
            "name": "cutpilot_export_fcpxml",
            "description": "Alias for cutpilot_export_fcp7xml (xmeml v4).",
            "inputSchema": fcp7_schema,
            "handler": self._tool_export_fcpxml
        }

        self.tools["cutpilot_verify_timeline"] = {
            "name": "cutpilot_verify_timeline",
            "description": "Performs readback verification of a timeline, checking clip placements, start frames, and duration.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "timeline_name": {"type": "string", "description": "Timeline to verify."},
                    "track_type": {"type": "string", "default": "video"},
                    "track_index": {"type": "integer", "default": 1}
                },
                "required": ["timeline_name"]
            },
            "handler": self._tool_verify_timeline
        }

    # ── Tool Handlers ──────────────────────────────────────────────────────────

    def _tool_inspect_project(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            curr = self.adapter.get_current_project()
            if not curr:
                return {"status": "NO_PROJECT_OPEN"}
            name = curr.GetName()
            tl_count = curr.GetTimelineCount()
            return {
                "status": "PASS",
                "project_name": name,
                "timeline_count": tl_count,
            }
        except Exception:
            # Fallback to direct SQLite reader
            target = args.get("project_name")
            if not target:
                raise ValueError("project_name is required when DaVinci Resolve bridge is unavailable")
            return self.sqlite.inspect_project(target)

    def _tool_inspect_timeline(self, args: Dict[str, Any]) -> Dict[str, Any]:
        tl_name = args["timeline_name"]
        track_type = args.get("track_type", "video")
        track_idx = int(args.get("track_index", 1))
        ver = self.adapter.verify_timeline(tl_name, track_type, track_idx)
        return ver.to_dict()

    def _tool_create_project(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = args["project_name"]
        existing = self.adapter.list_projects()
        if name in existing:
            self.adapter.load_project(name)
            return {"status": "LOADED_EXISTING", "project_name": name}
        ok = self.adapter.create_project(name)
        return {"status": "CREATED" if ok else "FAILED", "project_name": name}

    def _tool_import_media(self, args: Dict[str, Any]) -> Dict[str, Any]:
        path = args["file_path"]
        clip = self.adapter.import_media(path)
        return {
            "status": "PASS",
            "clip_name": clip.GetName() if clip else None,
            "source_path": path
        }

    def _tool_create_timeline(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = args["timeline_name"]
        fps = float(args.get("fps", 24.0))
        tl = self.adapter.ensure_timeline(name, fps=fps)
        return {
            "status": "PASS",
            "timeline_name": tl.GetName() if tl else name,
            "fps": fps
        }

    def _tool_place_clip(self, args: Dict[str, Any]) -> Dict[str, Any]:
        file_path = args["file_path"]
        start_frame = int(args["start_frame"])
        end_frame = int(args["end_frame"])
        track_type = args.get("track_type", "video")
        track_idx = int(args.get("track_index", 1))

        clip = self.adapter.import_media(file_path)
        appended = self.adapter.append_clip(clip, start_frame, end_frame, track_type, track_idx)
        return {
            "status": "PASS",
            "appended_count": len(appended) if isinstance(appended, list) else 1,
            "start_frame": start_frame,
            "end_frame": end_frame
        }

    def _tool_generate_captions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        words = args["words"]
        out_path = args["output_path"]
        fmt = args.get("format", "srt").lower()

        if fmt == "vtt":
            res = generate_vtt(words, out_path)
        else:
            res = generate_srt(words, out_path)

        return {"status": "PASS", "output_file": str(res), "format": fmt}

    def _tool_export_fcpxml(self, args: Dict[str, Any]) -> Dict[str, Any]:
        plan_data = args["plan"]
        out_path = args["output_path"]

        parts = [PartSource(**p) for p in plan_data.get("parts", [])]
        segs = [ClipSegment(**s) for s in plan_data.get("segments", [])]
        plan = CutPlan(
            parts=parts,
            segments=segs,
            fps=float(plan_data.get("fps", 30.0)),
            width=int(plan_data.get("width", 1920)),
            height=int(plan_data.get("height", 1080)),
            sequence_name=plan_data.get("sequence_name", "CutPilot Sequence")
        )
        res = FcpXmlGenerator.write_fcpxml(plan, out_path)
        return {"status": "PASS", "output_file": str(res)}

    def _tool_verify_timeline(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = args["timeline_name"]
        track_type = args.get("track_type", "video")
        track_idx = int(args.get("track_index", 1))
        ver = self.adapter.verify_timeline(name, track_type, track_idx)
        return ver.to_dict()

    # ── JSON-RPC Stdio Loop ────────────────────────────────────────────────────

    def handle_request(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION
                    }
                }
            }

        elif method == "tools/list":
            tools_list = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": t["inputSchema"]
                }
                for t in self.tools.values()
            ]
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": tools_list}
            }

        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            tool = self.tools.get(name)

            if not tool:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Tool '{name}' not found."}
                }

            try:
                res = tool["handler"](arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(res, indent=2)}
                        ],
                        "isError": False
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": f"Error executing tool '{name}': {str(e)}"}
                        ],
                        "isError": True
                    }
                }

        elif method == "notifications/initialized":
            return None

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method '{method}' not implemented."}
            }

    def run_stdio(self) -> None:
        """Runs the standard MCP stdio JSON-RPC loop."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                resp = self.handle_request(req)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"}
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()

def create_server() -> CutPilotMcpServer:
    return CutPilotMcpServer()

def main() -> None:
    server = create_server()
    server.run_stdio()

if __name__ == "__main__":
    main()
