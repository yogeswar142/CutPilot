"""
CutPilot MCP Server Package
Our canonical Model Context Protocol server exposing verified video-editing tools.
"""
from packages.cutpilot_mcp.server import create_server, main

__all__ = [
    "create_server",
    "main",
]
