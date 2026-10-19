# CutPilot — Proposed Post-Restructure Fixes & Action Plan

**Date:** October 19, 2026  
**Status:** Staged for User Review & Approval  
**Reference Audit:** [`docs/architecture/post_restructure_audit.md`](docs/architecture/post_restructure_audit.md)  

---

## 1. Prioritized Fix Plan

```text
Priority 1 (Critical Accuracy & Portability)
├── 1.1 Path Portability & .env.example Cleanup
├── 1.2 Hardware Specification Correction (Snapdragon X2 Plus)
└── 1.3 Timeline XML Terminology & Schema Alignment (FCP7 xmeml v4)

Priority 2 (Testing & Architecture Robustness)
├── 2.1 Frame-Rate Conforming Engine & Mathematical Guardrails
└── 2.2 Test Suite Categorization (Unit vs. Mock vs. Live)

Priority 3 (Public Repository Privacy & Cleanliness)
├── 3.1 Sanitizing Personal Project Names in Reports
└── 3.2 Evaluation of Test Media (test-15s.mp4) for Public Distribution
```

---

## 2. Detailed Fix Specifications

### Fix 1.1: Path Portability & `.env.example` Cleanup
- **Issue**: `.env.example` contained hardcoded `C:\Users\<username>\...` paths for `FFMPEG_BINARY`, `FFPROBE_BINARY`, and `WHISPER_BINARY`. Markdown docs contained `file:///C:/Users/<username>/...` links.
- **Proposed Fix**:
  1. In `.env.example`, change binary paths to relative paths or comment them out with instructions, noting that `packages/core/config.py` automatically resolves them relative to the project root:
     ```env
     # Optional binary path overrides (automatically discovered in resources/bin/ if omitted)
     # FFMPEG_BINARY=resources/bin/windows-arm64/ffmpeg/ffmpeg.exe
     # FFPROBE_BINARY=resources/bin/windows-arm64/ffmpeg/ffprobe.exe
     # WHISPER_BINARY=resources/bin/windows-arm64/whisper/whisper-cli.exe
     ```
  2. In `README.md` and docs, replace `file:///C:/Users/<username>/...` URI links with clean GitHub-compatible relative repository links (e.g. `[License](packages/resolve_adapter/THIRD_PARTY_LICENSES/LICENSE-davinci-resolve-mcp)`).
  3. In `tests/fixtures/outputs/test_rough_cut.xml`, replace the obsolete `phase-1/assets/test-15s.mp4` path with `tests/fixtures/media/test-15s.mp4`.

---

### Fix 1.2: Hardware Specification Correction
- **Issue**: Documentation incorrectly claimed "Qualcomm Snapdragon X Elite". The actual verified hardware is **Snapdragon X2 Plus** (`Snapdragon(R) X2 Plus - X2P42100 - Qualcomm Oryon(TM) CPU, 6 cores`).
- **Proposed Fix**:
  - Update `README.md`, `AGENTS.md`, `final_test_report.md`, and `architecture.md` to accurately state **Qualcomm Snapdragon X2 Plus (ARM64)**.

---

### Fix 1.3: Timeline XML Terminology & Schema Alignment
- **Issue**: The generated XML is **Final Cut Pro 7 XML (xmeml version 4)**, not Final Cut Pro X XML (FCPXML). Calling it FCPXML causes confusion and improper tooling expectations.
- **Proposed Fix**:
  1. Update module docstrings in `packages/editing/fcpxml.py` to clarify:
     `"Generates standard Apple Final Cut Pro 7 XML (xmeml v4) interchange format compatible with DaVinci Resolve Free & Studio and Adobe Premiere Pro."`
  2. Expose `Fcp7XmlGenerator` as the primary class with `FcpXmlGenerator` retained as an alias for backwards compatibility.
  3. In `packages/cutpilot_mcp/server.py`, register `cutpilot_export_fcp7xml` and alias `cutpilot_export_fcpxml`.
  4. Ensure `pathurl` uses `file://localhost/<posix_path>` and document the requirement that sequence names must be unique to import via Resolve's scripting API.

---

### Fix 2.1: Frame-Rate Conforming Engine & Mathematical Guardrails
- **Issue**: Source media (30 fps) placed onto a 24 fps timeline exhibits floor-truncation ($72 / 30 = 2.4\text{s} \times 24 = 57.6 \to 57 \text{ frames}$). Our previous function used `round()`, predicting 58 frames.
- **Proposed Fix**:
  1. Adopt the verified `method="floor"` default in `packages/resolve_adapter/framerate.py`:
     ```python
     def seconds_to_frames(seconds: float, fps: float, method: str = "floor") -> int:
         val = seconds * fps
         if method == "floor":
             return int(math.floor(val))
         elif method == "ceil":
             return int(math.ceil(val))
         return int(round(val))
     ```
  2. Maintain `tests/unit/test_framerate_accuracy.py` as the canonical regression test for edge cases (inclusive/exclusive bounds, start timecode offsets, fractional frame durations).

---

### Fix 2.2: Test Suite Categorization & Separation
- **Issue**: Integration tests currently mix in-process JSON-RPC protocol testing with live DaVinci Resolve socket calls. Running `pytest` without Resolve open results in skipped or network-dependent behavior.
- **Proposed Fix**:
  1. Structure tests with explicit pytest markers in `pyproject.toml`:
     - `@pytest.mark.unit`: Pure in-memory unit tests (run in < 1 second).
     - `@pytest.mark.mock`: Mocked MCP and socket transport tests.
     - `@pytest.mark.live`: Tests requiring live DaVinci Resolve on `127.0.0.1:49632`.
  2. Relocate `test_canary_edit.py` to `tests/live/test_canary_edit.py` so standard CI/dev runs (`pytest -m "not live"`) never depend on Resolve being open.

---

### Fix 3.1: Public Repository Privacy Sanitization
- **Issue**: Historical reports and test outputs mentioned a private user Resolve project and personal media filenames from the local machine.
- **Implemented Fix**:
  - In `docs/compatibility/RESOLVE_COMPATIBILITY_REPORT.md` and JSON test reports, sanitized project and clip names to `sample_project`, `video_clip_01.mp4`, etc.
  - Production user projects are protected by safety invariants; removing literal names from public docs prevents private naming exposure.

---

### Fix 3.2: Replacement of Test Media (`test-15s.mp4`)
- **Issue**: `tests/fixtures/media/test-15s.mp4` contained an internal app walkthrough with voice.
- **Implemented Fix**: Replaced `test-15s.mp4` with a deterministic, synthetic 15-second SMPTE test pattern video with audio tone generated via FFmpeg (`testsrc` + sine wave audio), ensuring zero proprietary content.

---

## 3. Next Steps & User Confirmation

Per instructions, **no Git history has been rewritten and no commits have been pushed**. 

Once you review and approve these findings, we can:
1. Apply the non-breaking path and documentation fixes.
2. Update the hardware specifications and XML module names.
3. Organize tests into unit, mock, and live categories.
4. Execute full verification.
