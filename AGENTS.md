# CutPilot — AI Agent Guidelines & Architecture Rules (`AGENTS.md`)

This document defines the core invariants, engineering standards, safety rules, and operational boundaries for AI coding agents (and human contributors) working on the CutPilot repository.

---

## 1. System Mission & Architectural Vision

CutPilot is an autonomous, model-independent video-editing copilot. It decomposes video post-production into three discrete agent stages:
1. **Agent 1 (Transcription & Audio)**: Extract audio, transcribe speech with sub-word timestamps using local ARM64 Whisper, enforce duration bounds.
2. **Agent 2 (Visual Analysis)**: Extract keyframes, analyze video semantics (shots, actions, speaker focus, visual quality) via multi-modal models.
3. **Agent 3 (Edit Planner & Conforming)**: Formulate an edit plan (rough cut, captioning, b-roll insertion), execute edits deterministically via `cutpilot-mcp` or `packages/resolve_adapter` into DaVinci Resolve Free 21.0.3+, and verify timeline state.

---

## 2. Package Boundaries & Responsibilities

The codebase follows a strict modular structure under `packages/`. Do not introduce circular dependencies or violate package boundaries:

| Package | Allowed Imports | Forbidden Imports | Primary Purpose |
|---|---|---|---|
| `packages.core` | Standard library only | Any other `packages.*` | Domain models, typed dataclasses, configuration, validation logic. |
| `packages.media` | `packages.core`, stdlib | `analysis`, `editing`, `resolve_adapter`, `cutpilot_mcp` | FFmpeg/FFprobe subprocess wrappers, audio extraction, frame dumping. |
| `packages.transcription`| `packages.core`, stdlib | `analysis`, `editing`, `resolve_adapter`, `cutpilot_mcp` | Local native ARM64 Whisper.cpp runner and token aggregation. |
| `packages.analysis` | `packages.core`, stdlib | `editing`, `resolve_adapter`, `cutpilot_mcp` | Gemini Video API calls, scene change & keyframe selection. |
| `packages.editing` | `packages.core`, stdlib | `cutpilot_mcp` | SRT/VTT caption generation, FCPXML generation, plan execution. |
| `packages.resolve_adapter` | `packages.core`, stdlib | `cutpilot_mcp`, `analysis`, `transcription` | Direct DaVinci Resolve in-app bridge client, framerate math, SQLite reader. |
| `packages.cutpilot_mcp`| All packages | None (top-level server) | Canonical Model Context Protocol (MCP) server exposing tools to external AI agents. |
| `packages.agents` | All packages | None (pipeline orchestrators) | High-level workflows for Agent 1, Agent 2, and Agent 3. |

---

## 3. Critical Safety Invariants ⚠️

Every agent modifying code or running automation scripts MUST strictly adhere to these safety rules:

### A. Project Protection & Target Scoping
- **NEVER modify or execute write operations against unverified user projects**.
- In-memory write operations and live testing **MUST ONLY** target designated disposable canary projects (specifically `CutPilot_Canary`).
- Always check the active project name before issuing edit or timeline commands. If the active project does not match the expected project, abort immediately.

### B. Frame Rate Math & Synchronization
- Video files and Resolve timelines often differ in frame rate:
  - Common source media is **30.0 fps** or **29.97 fps**.
  - Default DaVinci Resolve timelines initialize at **24.0 fps**.
  - A 2.4-second slice (72 frames at 30 fps) occupies **57 frames** at 24 fps ($2.4 \times 24 = 57.6 \to \lfloor 57.6 \rfloor = 57$ frames via Resolve floor conforming).
- **Never compare frame counts directly across different frame rates**.
- Always use `packages.resolve_adapter.framerate.convert_frame_bounds()` or perform calculations in normalized seconds (`time_seconds = frames / fps`).

### C. Cross-Platform Runtime & Architecture Integrity
- Detect the operating system and CPU architecture dynamically via `packages.core.platform`.
- **Never assume a specific username, machine path, or single CPU architecture**.
- Python, FFmpeg, Whisper, and DaVinci Resolve may run on differing architectures. Validate executable compatibility via `validate_binary_compatibility()` before launch.
- On Windows ARM64 systems:
  - Development Python is native ARM64 Python on the user's `PATH`.
  - DaVinci Resolve's Fusion engine (`fuscript.exe`) is an x64 binary requiring an isolated x64 Python runtime.
  - **DO NOT** alter system `PATH` to point to x64 Python.
  - Launch Resolve via `scripts/launch_resolve.bat`, which scopes `PYTHON3HOME` locally to the process.
- On standard Windows x64, macOS, and Linux systems: respect host native Python and tooling.

### D. Zero External Runtime Dependency Rule for Core Execution
- Core data classes (`packages.core.models`), validation, bridge client, captions, FCPXML, and MCP server are implemented using Python's standard library.
- External dependencies (like `pydantic`, `fastmcp`, `requests`) may be used as optional enhancements, but core functionality must remain functional without them.

---

## 4. MCP Server Conventions

When adding or modifying tools in `packages/cutpilot_mcp/server.py`:
1. Use standard MCP tool naming convention: `cutpilot_<action>_<noun>` (e.g., `cutpilot_inspect_project`, `cutpilot_place_clip`).
2. Provide comprehensive JSON Schemas with explicit descriptions for every parameter.
3. Every tool must return a standard dictionary:
   - Success: `{"success": True, ...payload}`
   - Error: `{"success": False, "error": "Descriptive message"}`
4. Do not crash the server process on operation errors; handle exceptions gracefully and return an error result.
5. All write operations must validate preconditions (active project, valid frame bounds) before dispatching to the adapter.

---

## 5. Coding & Testing Standards

- **Python Version**: Python 3.11+.
- **Type Annotations**: All public functions and classes must include type hints.
- **Docstrings**: Provide clear docstrings explaining inputs, outputs, and edge cases.
- **Unit Tests**: Located in `tests/unit/`. Must run in < 2 seconds without external network or DaVinci Resolve.
- **Integration Tests**: Located in `tests/integration/`. May connect to localhost bridge (`127.0.0.1:49632`).
- **Running Tests**:
  ```powershell
  # Standard test runner
  pytest

  # Live bridge verification
  python scripts/verify_bridge.py

  # Live canary edit execution
  python scripts/run_canary.py
  ```

---

## 6. Commit & Pull Request Guidelines

- Format commit messages with conventional commit prefixes:
  - `feat: <description>` for new capabilities
  - `fix: <description>` for bug fixes
  - `refactor: <description>` for internal code reorganizations
  - `test: <description>` for test additions
  - `docs: <description>` for documentation updates
- Never commit large binaries (`.exe`, `.dll`, `.bin`, `.gguf`) or raw video files to git. Use `resources/` with `.gitignore` and document download locations in `resources/models/manifest.json`.
