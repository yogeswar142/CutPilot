# ADR 0001: Model Context Protocol (MCP) and DaVinci Resolve Bridge Architecture

**Status:** Accepted  
**Date:** October 19, 2026  
**Context:** CutPilot Architecture Modernization  

---

## 1. Context & Problem Statement

CutPilot requires an autonomous bridge between AI reasoning agents (like Claude Desktop, Cursor, or Antigravity) and the video timeline editor (DaVinci Resolve Free 21.0.3.7 running on Windows 11 ARM64).

Challenges:
1. **DaVinci Resolve Free Edition Restrictions**: External Python scripting APIs (`fusionscript` / `DaVinciResolveScript`) are disabled by Blackmagic Design in the Free edition.
2. **Architecture Mismatch**: DaVinci Resolve on Windows is an x64 application. Its internal Fusion scripting console (`fuscript.exe`) cannot load the system's native ARM64 `python3.dll`.
3. **Agent Interoperability**: AI models require standardized tool-calling interfaces conforming to the Model Context Protocol (MCP).
4. **Environment Cleanliness**: Modifying system-wide environment variables (`PATH`, `PYTHONPATH`, `PYTHON3HOME`) to point to x64 Python breaks the user's native ARM64 development environment.

---

## 2. Decision

### 2.1 Canonical `cutpilot-mcp` Server
We establish an independent, native `cutpilot-mcp` server (`packages/cutpilot_mcp/server.py`) using the standard JSON-RPC 2.0 stdio transport conforming to MCP 2024-11-05.
- The server does not depend on third-party frameworks like FastMCP at runtime; it uses Python's standard library `sys`, `json`, and `typing`.
- 9 verified tools are exposed: project inspection, timeline inspection, project creation, media import, timeline creation, clip placement, timeline verification, caption generation, and FCPXML export.

### 2.2 In-App Bridge Architecture
We adapt the in-app loopback socket bridge architecture from `samuelgursky/davinci-resolve-mcp`:
- An internal Lua/Python script runs inside DaVinci Resolve's Fusion runtime, holding open a TCP server on `127.0.0.1:49632`.
- Commands sent over the socket are authenticated using HMAC-SHA256 with secrets stored in the user's local roaming AppData.
- A dedicated, lightweight launcher (`scripts/launch_resolve.bat`) sets `PYTHON3HOME` locally at process scope to `%LOCALAPPDATA%\Programs\Python\Python311-x64` before executing `Resolve.exe`, allowing `fuscript.exe` to load Python 3.11 x64 without touching system `PATH`.

### 2.3 Frame Rate Normalization
To prevent silent timeline drift between source media (typically 30.0 fps) and Resolve timelines (typically 24.0 fps), all clip placements must use explicit mathematical conversion via `packages/resolve_adapter/framerate.py`:
$$\text{timeline\_frames} = \text{round}\left(\text{source\_frames} \times \frac{\text{timeline\_fps}}{\text{source\_fps}}\right)$$

### 2.4 Zero External Runtime Dependencies
All core data models (`packages/core/models.py`), schema validation (`packages/core/validation.py`), socket communication (`packages/resolve_adapter/bridge_client.py`), and XML/caption generators are implemented using standard library primitives to guarantee zero installation friction and fast startup.

---

## 3. Consequences

### Positive:
- **Rock-solid Free Edition Automation**: Direct timeline creation and clip placement work reliably on DaVinci Resolve Free 21.0.3.7.
- **System Integrity**: User's ARM64 environment is completely protected; no global environment variables are altered.
- **Agent Agnostic**: Any MCP-compliant client can interact with CutPilot tools out-of-the-box.
- **Fast Execution**: Tests run in ~1.2s without heavy import overhead.

### Negative / Trade-offs:
- User must run `resolve_bridge` from Workspace → Scripts once when starting Resolve to open the socket listener.
- Scripting operations in the Free edition must execute through the registered operations of the in-app bridge rather than arbitrary external script handles.
