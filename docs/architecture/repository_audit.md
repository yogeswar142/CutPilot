# CutPilot — Repository Audit & Migration Plan

**Date:** October 19, 2026  
**Auditor:** Antigravity AI Engineering  
**Version:** 1.0.0  
**Target Architecture:** Multi-package Modular MCP Architecture  

---

## 1. Executive Summary

This audit evaluates the entire CutPilot repository following the completion of Phase 1 (local speech transcription & cloud visual analysis) and Phase 2 (DaVinci Resolve compatibility & live canary timeline editing).

The codebase currently spans two flat directories (`phase-1/` and `phase-2/`) containing working production components, diagnostic scripts, experimental benchmarks, native binaries, reference repositories, and temporary outputs. While core capabilities are functional and verified on Windows 11 ARM64 and DaVinci Resolve Free 21.0.3.7, the layout lacks separation of concerns, formal package boundaries, shared contracts, and a unified MCP service interface.

This document classifies every file, details external dependencies and licenses, resolves architectural discrepancies (such as timeline vs source frame rates), and defines the canonical restructuring plan.

---

## 2. Complete File Inventory & Classification

Every file in the repository is classified into one of four actions:
- **`Keep`**: Active production implementation or canonical asset/binary.
- **`Refactor`**: Working code to be adapted into modular packages (`packages/`).
- **`Archive`**: Historical benchmark evidence, experimental spikes, and diagnostic runs retained for reproducibility (`archive/`).
- **`Remove`**: Disposable temporary artifacts, build caches, and unneeded downloads.

### 2.1 Phase 1 Inventory

| Path | Size | Description | Classification | Target Destination |
|---|:---:|---|:---:|---|
| `phase-1/assets/test-15s.mp4` | 5.27 MB | Canonical 15s 720p 30fps test video | **Keep** | `tests/fixtures/media/test-15s.mp4` |
| `phase-1/bin/ffmpeg.exe`, `ffprobe.exe`, DLLs | 34.6 MB | Native ARM64 FFmpeg 7.1 suite | **Keep** | `resources/bin/windows-arm64/ffmpeg/` |
| `phase-1/bin/Release/whisper-cli.exe`, DLLs | 9.6 MB | Native ARM64 Whisper.cpp suite | **Keep** | `resources/bin/windows-arm64/whisper/` |
| `phase-1/models/ggml-base.bin` | 141 MB | Whisper Base GGML model weights | **Keep** | `resources/models/whisper/` (Git-ignored) |
| `phase-1/scripts/agent1_transcript.py` | 5.4 KB | Whisper CLI word timestamp extraction | **Refactor** | `packages/transcription/` & `packages/agents/` |
| `phase-1/scripts/agent2_video_analysis.py` | 6.8 KB | Video understanding & state analysis | **Refactor** | `packages/analysis/` & `packages/agents/` |
| `phase-1/scripts/run_validation.py` | 3.2 KB | Timestamp & bounds validator | **Refactor** | `packages/core/validation.py` |
| `phase-1/scripts/benchmark_cloud_video.py` | 4.8 KB | Gemini 3.8/2.5-flash video benchmark | **Archive** | `archive/experiments/phase-1/benchmarks/` |
| `phase-1/scripts/benchmark_instruct_model.py`| 5.1 KB | Qwen3-VL 4B Instruct benchmark | **Archive** | `archive/experiments/phase-1/benchmarks/` |
| `phase-1/scripts/benchmark_keyframe_selection.py` | 4.2 KB | Scene cut & frame difference selector | **Refactor / Archive** | `packages/analysis/keyframe_selector.py` |
| `phase-1/experimental/llama_opencl_adreno/` | 18.2 MB | Experimental OpenCL llama runner | **Archive** | `archive/experiments/phase-1/experimental/` |
| `phase-1/experimental/ollama_opencl_test/` | 12.4 MB | Experimental Ollama OpenCL test | **Archive** | `archive/experiments/phase-1/experimental/` |
| `phase-1/test-results/*.md`, `*.json` | ~150 KB | Phase 1 benchmark reports & metrics | **Archive** | `archive/experiments/phase-1/test-results/` |
| `phase-1/outputs/*` | Variable | Intermediate WAVs, frames, JSON caches | **Archive / GitIgnore**| `artifacts/temporary/` |

### 2.2 Phase 2 Inventory

| Path | Size | Description | Classification | Target Destination |
|---|:---:|---|:---:|---|
| `phase-2/adapter/captions_generator.py` | 3.8 KB | Word-timestamp to SRT/VTT generator | **Refactor** | `packages/editing/captions.py` |
| `phase-2/adapter/fcpxml_generator.py` | 5.1 KB | FCPXML (xmeml v4) timeline generator | **Refactor** | `packages/editing/fcpxml.py` |
| `phase-2/adapter/project_inspector.py` | 3.3 KB | Direct SQLite `Project.db` reader | **Refactor** | `packages/resolve-adapter/sqlite_inspector.py` |
| `phase-2/adapter/test_adapter.py` | 3.9 KB | Adapter test harness | **Refactor** | `tests/integration/test_adapter.py` |
| `phase-2/launch_resolve.bat` | 0.5 KB | Isolated x64 environment launcher | **Keep** | `scripts/launch_resolve.bat` |
| `phase-2/test_first_edit.py` | 7.8 KB | Verified live canary edit script | **Refactor** | `tests/integration/test_canary_edit.py` |
| `phase-2/verify_mcp_query.py` | 2.5 KB | Fast read-only query check | **Refactor** | `scripts/verify_bridge.py` |
| `phase-2/test_inspect.py` | 3.3 KB | Diagnostic SQLite inspector | **Archive** | `archive/experiments/phase-2/diagnostics/` |
| `phase-2/test_lua.lua` | 33 B | Diagnostic Lua probe | **Archive** | `archive/experiments/phase-2/diagnostics/` |
| `phase-2/test_python_fuscript.py` | 66 B | Diagnostic fuscript probe | **Archive** | `archive/experiments/phase-2/diagnostics/` |
| `phase-2/test_captions.srt`, `test_rough_cut.xml` | 5.8 KB | Verified generated artifacts | **Keep** | `tests/fixtures/outputs/` |
| `phase-2/REPOSITORY_AUDIT.md` | 8.0 KB | Early audit of upstream reference repos| **Refactor** | `docs/architecture/upstream_audit.md` |
| `phase-2/RESOLVE_COMPATIBILITY_REPORT.md` | 7.9 KB | Live compatibility report (21.0.3.7) | **Keep** | `docs/compatibility/resolve_21_0_report.md` |
| `phase-2/TOOL_INTERFACE.md` | 7.3 KB | Early tool specification | **Refactor** | `docs/architecture/tool_contracts.md` |
| `phase-2/test-results/first_edit_canary.md`| 5.8 KB | Canary edit verification report | **Keep** | `docs/compatibility/first_edit_canary.md` |
| `phase-2/test-results/first_edit_canary_raw.json`| 3.2 KB | Raw execution telemetry | **Keep** | `artifacts/reports/first_edit_canary_raw.json` |
| `phase-2/bridge_verification_result.json`| 0.5 KB | Bridge query verification record | **Keep** | `artifacts/reports/bridge_verification.json` |
| `phase-2/adapter_verification_summary.json` | 0.7 KB | Adapter suite verification record | **Keep** | `artifacts/reports/adapter_verification.json` |
| `phase-2/python-x64/` | 18 MB | Downloaded Python 3.11.9 x64 archive | **Remove / Ignore** | Installed to `%LOCALAPPDATA%`, remove archive |
| `phase-2/reference/davinci-resolve-mcp/` | 2.5 MB | Upstream MIT reference repository | **Keep Reference** | `reference/davinci-resolve-mcp/` (Ignored) |
| `phase-2/reference/videopowers/` | 4.2 MB | Upstream MIT reference repository | **Keep Reference** | `reference/videopowers/` (Ignored) |

---

## 3. Reference Repositories & License Attribution

CutPilot adapts code from two open-source MIT-licensed projects:

### 3.1 `samuelgursky/davinci-resolve-mcp` (MIT License)
- **What is Adapted**:
  - The in-app HTTP bridge transport (`resolve_bridge.py`, HMAC SHA-256 handshake, nonces, loopback socket server).
  - The transparent proxy client (`resolve_bridge_client.py`, LRU handle management, method reflection).
- **What is Avoided**:
  - External scripting fallback for Studio edition (unviable on Free edition).
  - Heavy monolithic CLI / server design.
- **License Requirement**: Full MIT license preserved in `packages/resolve-adapter/THIRD_PARTY_LICENSES/LICENSE-davinci-resolve-mcp`.

### 3.2 `vinit-agr/videopowers` (MIT License)
- **What is Adapted**:
  - Deterministic FCPXML (xmeml v4) timeline generator logic with frame-accurate edit points and trimmable handles.
  - SRT/VTT caption chunking heuristics from transcript word streams.
- **What is Avoided**:
  - Remotion / React visual rendering dependencies and TypeScript orchestration.
- **License Requirement**: Full MIT license preserved in `packages/editing/THIRD_PARTY_LICENSES/LICENSE-videopowers`.

---

## 4. Key Architectural Findings & Technical Debt

### 4.1 Frame Rate Discrepancy Resolution (72 vs 57 Frames)
- **Observation**: In the Phase 3.1 canary test, `startFrame: 0, endFrame: 72` resulted in a placed timeline clip spanning `86400` to `86457` (57 frames).
- **Root Cause**:
  - The source video (`phase-1/assets/test-15s.mp4`) has a native frame rate of **30.0 fps** ($72 / 30 = 2.400$ seconds).
  - DaVinci Resolve's default timeline for new projects initializes at **24.0 fps**.
  - Placing a 2.4-second source span onto a 24 fps timeline produces $2.4 \times 24 = 57.6$ frames, which truncates to **57 timeline frames**.
- **Architectural Remedy**:
  The new `packages/resolve-adapter/framerate.py` module explicitly detects source media frame rates and configures timeline settings to match the primary footage fps, or calculates frame-rate conversions deterministically.

### 4.2 Architecture Mismatch on Windows 11 ARM64
- `Resolve.exe` and `fuscript.exe` run as x64 under Prism emulation.
- System `PATH` hosts native ARM64 Python.
- Scoping `Python311-x64` to Resolve's process via `scripts/launch_resolve.bat` completely solved the crash without polluting the user's global environment.

---

## 5. Migration Execution Strategy

The migration is executed across three non-destructive stages:

1. **Scaffold Canonical Structure**:
   Create root configuration (`pyproject.toml`, `.env.example`, `README.md`, `AGENTS.md`, `CHANGELOG.md`), package directories (`packages/`), test suites (`tests/`), and documentation (`docs/`).
2. **Port & Modularize Core Capabilities**:
   - `packages/core/`: Pydantic data schemas, validation, configuration.
   - `packages/media/`: FFmpeg / FFprobe wrapper.
   - `packages/transcription/`: Whisper.cpp integration.
   - `packages/analysis/`: Gemini visual analyzer & keyframe selector.
   - `packages/editing/`: FCPXML generator & captions generator.
   - `packages/resolve-adapter/`: Bridge client, SQLite inspector, and Resolve API wrapper.
   - `packages/cutpilot-mcp/`: Canonical Model Context Protocol server.
3. **Archive & Clean**:
   Move benchmark scripts and raw historical runs into `archive/experiments/`.
   Verify all imports and tests pass.
