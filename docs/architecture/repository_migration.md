# CutPilot — Repository Migration & Execution Record

**Date:** October 19, 2026  
**Status:** In Progress / Executing  
**Version:** 1.0.0  

---

## 1. Migration Overview

This document records the exact steps taken to transform the initial exploration workspace (`phase-1/` and `phase-2/`) into the modular production architecture defined in [`docs/architecture/architecture.md`](docs/architecture/architecture.md).

### Guiding Rules:
1. **Zero Data Loss**: No code or verified benchmark evidence is deleted without archiving.
2. **Reversible Commits**: Git commits record the state before, during, and after each stage.
3. **Safety Protection**: Existing projects and native ARM64 Python on `PATH` remain untouched.
4. **Independent Maintainability**: CutPilot packages do not depend on external repositories directly at runtime; upstream code is adapted cleanly with full MIT attribution.

---

## 2. Directory Creation Matrix

The following directory tree is scaffolded in the repository root:

```text
CutPilot/
├── packages/
│   ├── core/                    # Shared Pydantic models, contracts, validation
│   ├── media/                   # FFmpeg / FFprobe wrapper and audio extraction
│   ├── transcription/           # Native ARM64 Whisper.cpp integration
│   ├── analysis/                # Video understanding & keyframe selector
│   ├── editing/                 # FCPXML, captions generator, edit execution
│   ├── resolve_adapter/         # In-app bridge client & Resolve API abstraction
│   ├── cutpilot_mcp/            # Canonical Model Context Protocol server
│   └── agents/                  # Agent 1, Agent 2, Agent 3 workflows
│
├── resources/
│   ├── bin/windows-arm64/       # Native ARM64 FFmpeg & Whisper binaries
│   ├── models/                  # Manifest for model weights
│   └── templates/               # Caption & FCPXML templates
│
├── tests/
│   ├── unit/                    # Fast isolated tests for models and generators
│   ├── integration/             # Live adapter, bridge, and pipeline tests
│   └── fixtures/                # Test video assets and sample outputs
│
├── docs/
│   ├── architecture/            # System specs, contracts, audit
│   ├── compatibility/           # DaVinci Resolve compatibility reports
│   ├── development/             # Developer guide and onboarding
│   └── decisions/               # Architecture Decision Records (ADRs)
│
├── scripts/                     # Launch scripts, diagnostics, verification
├── artifacts/                   # Local reports, logs, temporary outputs (git-ignored)
└── archive/                     # Preserved historical experiments and raw benchmarks
```

---

## 3. File Migration Plan

| Original Location | Target Location | Action |
|---|---|:---:|
| `phase-1/assets/test-15s.mp4` | `tests/fixtures/media/test-15s.mp4` | Copy & Preserve |
| `phase-1/bin/*` | `resources/bin/windows-arm64/ffmpeg/` | Move & Retain |
| `phase-1/bin/Release/*` | `resources/bin/windows-arm64/whisper/` | Move & Retain |
| `phase-1/models/ggml-base.bin` | `resources/models/whisper/ggml-base.bin` | Move & Git-ignore |
| `phase-1/scripts/agent1_transcript.py` | `packages/transcription/whisper_runner.py` | Refactor |
| `phase-1/scripts/agent2_video_analysis.py` | `packages/analysis/gemini_analyzer.py` | Refactor |
| `phase-1/scripts/run_validation.py` | `packages/core/validation.py` | Refactor |
| `phase-1/scripts/benchmark_keyframe_selection.py` | `packages/analysis/keyframe_selector.py` | Refactor |
| `phase-1/test-results/*` | `archive/experiments/phase-1/test-results/` | Archive |
| `phase-1/experimental/*` | `archive/experiments/phase-1/experimental/` | Archive |
| `phase-1/outputs/*` | `archive/experiments/phase-1/outputs/` | Archive |
| `phase-2/adapter/captions_generator.py` | `packages/editing/captions.py` | Refactor |
| `phase-2/adapter/fcpxml_generator.py` | `packages/editing/fcpxml.py` | Refactor |
| `phase-2/adapter/project_inspector.py` | `packages/resolve_adapter/sqlite_inspector.py` | Refactor |
| `phase-2/launch_resolve.bat` | `scripts/launch_resolve.bat` | Refactor |
| `phase-2/test_first_edit.py` | `tests/integration/test_canary_edit.py` | Refactor |
| `phase-2/verify_mcp_query.py` | `scripts/verify_bridge.py` | Refactor |
| `phase-2/RESOLVE_COMPATIBILITY_REPORT.md` | `docs/compatibility/RESOLVE_COMPATIBILITY_REPORT.md` | Move |
| `phase-2/test-results/first_edit_canary.md` | `docs/compatibility/first_edit_canary.md` | Move |
| `phase-2/test_captions.srt` | `tests/fixtures/outputs/test_captions.srt` | Move |
| `phase-2/test_rough_cut.xml` | `tests/fixtures/outputs/test_rough_cut.xml` | Move |
| `phase-2/test_inspect.py`, `test_lua.lua`, `test_python_fuscript.py` | `archive/experiments/phase-2/diagnostics/` | Archive |
| `phase-2/python-x64/` | Deleted (Installed to `%LOCALAPPDATA%`) | Remove |
| `phase-2/reference/` | `reference/` (Git-ignored) | Move |

---

## 4. Verification Checkpoints

1. [x] Scaffold package files and `pyproject.toml`. (Completed)
2. [x] Migrate `packages/core` and run unit tests. (Completed)
3. [x] Migrate `packages/media`, `packages/transcription`, and `packages/analysis`. (Completed)
4. [x] Migrate `packages/editing` and `packages/resolve_adapter`. (Completed)
5. [x] Implement canonical `packages/cutpilot_mcp` with 9 verified tools. (Completed)
6. [x] Run full verification suite against live Resolve bridge (`127.0.0.1:49632`). (Completed - 16/16 tests pass)
7. [x] Update documentation (`README.md`, `AGENTS.md`, `final_test_report.md`, ADRs) and commit. (Completed)

---

## 5. Post-Migration Verification Summary

- **Automated Tests**: 16/16 passed in 1.23 seconds (`pytest`).
- **Live Bridge Health**: Verified via `python scripts/verify_bridge.py`.
- **Canary Timeline Edit**: Verified via `python scripts/run_canary.py` with frame-rate translation ($72 \to 57$ frames).
- **Safety Protection**: User projects confirmed untouched and intact.
- **Attribution**: Third-party MIT licenses preserved in `packages/resolve_adapter/THIRD_PARTY_LICENSES/` and `packages/editing/THIRD_PARTY_LICENSES/`.
