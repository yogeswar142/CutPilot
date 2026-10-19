# Changelog

All notable changes to the CutPilot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-19

### Added
- **Canonical Model Context Protocol Server (`packages/cutpilot_mcp`)**: Full JSON-RPC 2.0 stdio server providing 9 verified editing and inspection tools for Claude Desktop, Cursor, and Antigravity.
- **DaVinci Resolve Bridge Adapter (`packages/resolve_adapter`)**:
  - `bridge_client.py`: HMAC-SHA256 authenticated loopback client communicating with Resolve Free 21.0.3.7 on `127.0.0.1:49632`.
  - `adapter.py`: High-level Python editing interface for project creation, media pool import, timeline creation, and clip placement.
  - `framerate.py`: Source-to-timeline frame rate math preventing silent drift across 30.0 fps media and 24.0 fps timelines.
  - `sqlite_inspector.py`: Direct SQLite project database reader for offline inspection.
- **Domain Models & Validation (`packages/core`)**: Typed dataclasses (`MediaAsset`, `WordTimestamp`, `TranscriptResult`, `VisualEvent`, `EditPlan`, `OperationRecord`) and validation logic with zero external pip dependencies.
- **Media Processing Package (`packages/media`)**:
  - `inspector.py`: Native ARM64 `ffprobe` video and audio metadata inspection.
  - `audio.py`: 16kHz mono WAV extraction for Whisper.
  - `video.py`: Keyframe extraction and silent video proxy generation.
- **Native ARM64 Transcription (`packages/transcription`)**:
  - `whisper_runner.py`: Native ARM64 `whisper-cli.exe` runner with subword token aggregation and strict duration ceiling enforcement.
- **Visual Analysis Package (`packages/analysis`)**:
  - `gemini_analyzer.py`: Multi-modal video analysis via Google Gemini Video API.
  - `keyframe_selector.py`: Scene-cut and frame-diff keyframe selection.
- **Editing & Conforming Package (`packages/editing`)**:
  - `captions.py`: Subtitle generator for SRT and WebVTT formats with configurable line length and duration chunking.
  - `fcpxml.py`: Final Cut Pro XML (xmeml v4) timeline generator.
  - `plan_executor.py`: Sequential edit plan execution and state verification engine.
- **Autonomous Agent Workflows (`packages/agents`)**: Scaffolding for Agent 1 (Speech), Agent 2 (Visuals), and Agent 3 (Planner).
- **Automated Test Suite (`tests/`)**:
  - 12 unit tests covering models, validation, framerate math, and caption formatting.
  - 4 integration tests covering live canary timeline editing and MCP server initialization/tool dispatch.
- **Safety Scripts (`scripts/`)**:
  - `launch_resolve.bat`: Safe process-level launcher setting `PYTHON3HOME` to x64 Python for DaVinci Resolve without altering system `PATH`.
  - `verify_bridge.py`: CLI healthcheck for the in-app bridge listener.
  - `run_canary.py`: Live canary edit verification script targeting `CutPilot_Canary`.
- **Comprehensive Documentation (`docs/`)**:
  - System architecture specification (`docs/architecture/architecture.md`).
  - Repository audit and inventory (`docs/architecture/repository_audit.md`).
  - Migration record (`docs/architecture/repository_migration.md`).
  - Final test report (`docs/development/final_test_report.md`).
  - Architecture Decision Record (`docs/decisions/0001-mcp-and-resolve-bridge-architecture.md`).
  - DaVinci Resolve compatibility report (`docs/compatibility/RESOLVE_COMPATIBILITY_REPORT.md`).
  - Canary edit report (`docs/compatibility/first_edit_canary.md`).
- **Third-Party Attribution**: Explicit licenses and attributions preserved for `davinci-resolve-mcp` and `videopowers`.

### Changed
- Complete repository reorganization from exploratory `phase-1/` and `phase-2/` directories into a modular production architecture under `packages/`.
- Updated desktop shortcut `DaVinci Resolve (CutPilot Bridge).lnk` to execute `scripts/launch_resolve.bat`.
- Configured pytest with `pythonpath = ["."]` in `pyproject.toml`.

### Archived
- Preserved 100% of historical Phase 1 and Phase 2 benchmarks, hardware feasibility studies, diagnostics, and raw test results under `archive/experiments/`.

### Removed
- Removed disposable `phase-2/python-x64/` unpack directory (superseded by official user installation in `%LOCALAPPDATA%\Programs\Python\Python311-x64`).
- Cleaned up obsolete cache directories and duplicate test scripts.
