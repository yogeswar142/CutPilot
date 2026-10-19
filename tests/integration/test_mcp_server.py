"""
Integration Tests for CutPilot MCP Server
"""
import pytest
from packages.cutpilot_mcp.server import create_server

@pytest.mark.mock
def test_mcp_server_initialize():
    server = create_server()
    resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    })
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "cutpilot-mcp"
    assert resp["result"]["serverInfo"]["version"] == "1.0.0"

@pytest.mark.mock
def test_mcp_tools_list():
    server = create_server()
    resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    })
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "cutpilot_inspect_project" in tool_names
    assert "cutpilot_create_project" in tool_names
    assert "cutpilot_import_media" in tool_names
    assert "cutpilot_create_timeline" in tool_names
    assert "cutpilot_place_clip" in tool_names
    assert "cutpilot_generate_captions" in tool_names
    assert "cutpilot_export_fcp7xml" in tool_names
    assert "cutpilot_export_fcpxml" in tool_names
    assert "cutpilot_verify_timeline" in tool_names

@pytest.mark.mock
def test_mcp_generate_captions_tool(tmp_path):
    server = create_server()
    out_file = str(tmp_path / "test_subs.srt")
    words = [
        {"word": "Welcome", "start": 0.0, "end": 0.5},
        {"word": "to", "start": 0.5, "end": 0.7},
        {"word": "CutPilot.", "start": 0.7, "end": 1.2}
    ]
    resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "cutpilot_generate_captions",
            "arguments": {
                "words": words,
                "output_path": out_file,
                "format": "srt"
            }
        }
    })
    assert resp["result"]["isError"] is False
    assert "PASS" in resp["result"]["content"][0]["text"]
