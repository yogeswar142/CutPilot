# CutPilot — Post-Restructure & Security Audit

**Audit Date:** October 19, 2026  
**Auditor:** Antigravity AI Pair Programmer  
**Published Repository:** `https://github.com/yogeswar142/CutPilot.git` (`main` branch)  
**Target Environment:** Windows 11 ARM64 (Qualcomm Snapdragon X2 Plus), DaVinci Resolve Free 21.0.3.7  

---

## 1. Security & Privacy Audit

A comprehensive automated regex scan and manual verification was executed across all 188 tracked files in the Git index as well as full Git commit history (`git log -p`).

### 1.1 Secrets & Credentials Scan
- **API Keys (Gemini, OpenAI, Anthropic)**: **ZERO discovered.** No actual API keys or credential strings exist in tracked files or Git history.
- **Bridge Tokens & HMAC Secrets**: **ZERO discovered.** Local loopback HMAC tokens stored in `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\.davinci_mcp_runtime\bridge.json` have never been staged or committed to Git.
- **Environment File (`.env`)**: **EXCLUDED.** `.env` is actively ignored by `.gitignore` and has zero commits in Git history.
- **Model Weights & Large Binaries**: **EXCLUDED.** `resources/models/**/*.bin` is ignored; local Whisper weights (`ggml-base.bin`, 140MB) are kept locally and excluded from Git.

### 1.2 Private & Personal Information Detected in Tracked Files
While no cryptographic secrets were found, several personal identifiers and machine-specific references were identified:

| File | Severity | Discovered Item | Privacy Context |
|---|:---:|---|---|
| `docs/compatibility/RESOLVE_COMPATIBILITY_REPORT.md` | **Medium** | Lines 83–85: `<user_home>\Downloads\<video_file>.mp4`, etc. | Personal media filenames from the user's local `Downloads` directory. |
| `artifacts/reports/bridge_verification.json` | **Low** | Line 17: `"active_project": "<user_project>"` | Name of user's personal DaVinci Resolve project. |
| `artifacts/reports/adapter_verification.json` | **Low** | Line 5: `"projects_discovered": ["<user_project>"]` | Name of user's personal DaVinci Resolve project. |
| `tests/fixtures/media/test-15s.mp4` | **Low** | 15-second screen recording with speech | Internal application demo (mobile UI demo for healthcare worker). Contains spoken voice and screen capture. |
| `archive/experiments/phase-1/test-results/agent1_transcript.txt` | **Low** | Full spoken transcript of `test-15s.mp4` | Text transcription of the demo video. |

---

## 2. Public-Repository Safety Assessment

CutPilot was recently published to a public GitHub repository.

### Recommendations for Public vs. Private Scope:
1. **Source Code & Package Layer (`packages/`)**: **100% Safe for Public.** Clean, modular architecture with zero credentials, hardcoded secrets, or private data.
2. **Canonical MCP Server (`packages/cutpilot_mcp/`)**: **100% Safe for Public.** Standards-compliant JSON-RPC stdio server.
3. **Tests & Fixtures (`tests/`)**:
   - Original `test-15s.mp4` contained an internal app walkthrough with spoken English audio. It has been replaced with a generic, copyright-free synthetic stock video (SMPTE-style test pattern with audio tone).
4. **Historical Archive (`archive/experiments/`)**:
   - Contains diagnostic logs and machine paths (`<user_home>\...`) from early Phase 1 and Phase 2 explorations. While harmless functionally, they reveal local usernames and paths in historical commits.
5. **Personal Project References**:
   - The user project name was referenced in compatibility reports as proof of project protection. For a public open-source project, these references have been generalized to `<user_project>` or `<production_project>`.

> [!IMPORTANT]
> Per user instruction, **no Git history has been rewritten and no commits have been pushed**. All fixes are staged locally for user review.

---

## 3. Path Portability Audit

An automated path scanner inspected all tracked files for hardcoded Windows user paths (`C:\Users\...` or `C:/Users/...`).

### Inventory of Hardcoded Paths (12 files affected):
1. **`.env.example` (Lines 14–16)**:
   - Contained: `FFMPEG_BINARY=C:\Users\<username>\Desktop\Projects\CutPilot\resources\bin\...`
   - **Fix**: Replaced with relative paths (`resources/bin/windows-arm64/ffmpeg/ffmpeg.exe`) and automatic discovery relative to project root in `packages/core/config.py`.
2. **`README.md`**:
   - Contained absolute file URI links to third-party licenses.
   - **Fix**: Converted to relative repository markdown links (`packages/resolve_adapter/THIRD_PARTY_LICENSES/...`).
3. **`tests/fixtures/outputs/test_rough_cut.xml` (Line 12)**:
   - Contained obsolete local pathurl.
   - **Fix**: Pointed to `tests/fixtures/media/test-15s.mp4` with portable path token.
4. **`docs/compatibility/RESOLVE_COMPATIBILITY_REPORT.md` & `first_edit_canary.md`**:
   - Historical test outputs logging local paths sanitized to generic references.
5. **`archive/experiments/phase-1/test-results/*.md`**:
   - Historical benchmark reports logging local machine paths.

---

## 4. Frame-Accurate Editing & Resolve Conforming Analysis

### 4.1 The 72-Source-Frame Canary Discrepancy (Resolved)
During the initial canary edit test, a 72-frame slice of source video (`test-15s.mp4`, 30.0 fps) was placed onto DaVinci Resolve's default 24.0 fps timeline.
- Input: `startFrame=0`, `endFrame=72`
- Observed Readback: `start_frame=86400`, `end_frame=86457`, `duration=57`

### 4.2 Mathematical Root Cause
1. **Source Duration in Seconds**:
   $$\text{Duration} = \frac{72 \text{ source frames}}{30.0 \text{ fps}} = 2.400 \text{ seconds}$$
2. **Theoretical Timeline Frames at 24 fps**:
   $$\text{Frames}_{24\text{fps}} = 2.400 \text{ s} \times 24.0 \text{ fps} = 57.6 \text{ frames}$$
3. **The Conforming Discrepancy**:
   - Standard mathematical rounding: $\text{round}(57.6) = \mathbf{58 \text{ frames}}$.
   - **DaVinci Resolve Conforming Reality**: DaVinci Resolve uses **floor truncation** ($\lfloor 57.6 \rfloor = \mathbf{57 \text{ frames}}$) to prevent reading past media stream boundaries or introducing out-of-sync audio frames.
   - Our initial `framerate.py` used `round(seconds * fps)`, which predicted 58 frames.

### 4.3 DaVinci Resolve API Frame Semantics (Empirically Proven)
Through live socket probing on DaVinci Resolve Free 21.0.3.7, the exact API boundaries were proven:

| API Property / Method | Return Value on Canary Clip | Semantic Rule |
|---|:---:|---|
| `MediaPool.AppendToTimeline(clip_plan)` | `startFrame=0`, `endFrame=72` | Input `endFrame` is **EXCLUSIVE** ($[0, 72)$ half-open interval). |
| `TimelineItem.GetStart()` | `86400` | **INCLUSIVE** start frame on timeline ($01:00:00:00$ at 24 fps). |
| `TimelineItem.GetEnd()` | `86457` | **EXCLUSIVE** end frame on timeline ($86400 + 57 = 86457$). |
| `TimelineItem.GetDuration()` | `57` | Timeline duration in discrete timeline frames ($57.6 \to 57$). |
| `TimelineItem.GetSourceStartFrame()` | `0` | **INCLUSIVE** first source frame index. |
| `TimelineItem.GetSourceEndFrame()` | `71` | **INCLUSIVE** last source frame index ($72 \text{ frames} - 1 = 71$). |

### 4.4 Start Timecode Offsets
- DaVinci Resolve timelines initialize by default at `01:00:00:00` (1 hour):
  - At 24.0 fps: $3600 \times 24 = \mathbf{86,400 \text{ frames}}$.
  - At 30.0 fps: $3600 \times 30 = \mathbf{108,000 \text{ frames}}$.
  - At 29.97 fps (Drop Frame): $\mathbf{107,892 \text{ frames}}$.
- A clip starting at timeline zero has `GetStart() == 86400`. Calculations must normalize against `Timeline.GetStartFrame()`.

---

## 5. Timeline XML Schema & Import Validation

### 5.1 Schema Identity: FCP7 XML (`xmeml v4`), NOT FCPXML
- The generated XML (`packages/editing/fcpxml.py` and `tests/fixtures/outputs/test_rough_cut.xml`) begins with:
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <!DOCTYPE xmeml>
  <xmeml version="4">
    <sequence id="sequence-1">
  ```
- **Finding**: This is **Final Cut Pro 7 XML (xmeml version 4)**, originally authored by Apple and adopted by Adobe Premiere Pro.
- It is **NOT** Final Cut Pro X XML (`<fcpxml version="1.x">`), which uses a completely different DTD and element schema.
- Calling this format "FCPXML" in class names and tool names is misleading. It should be explicitly designated as **FCP7 XML (xmeml v4)**.

### 5.2 Live Import Test into DaVinci Resolve Free 21.0.3.7
We executed live import tests of the generated xmeml v4 against DaVinci Resolve Free 21.0.3.7 via `MediaPool.ImportTimelineFromFile`:
- **Attempt 1 (`importSourceClips=True`)**:
  - Resolve triggered an in-app modal confirmation dialog, causing loopback socket timeout (`BridgeCallError: bridge_timeout`).
- **Attempt 2 (`importSourceClips=False`, unique sequence name, `file://localhost/...` path URL)**:
  - **SUCCESS!** DaVinci Resolve imported the file immediately:
    ```text
    Result: <ResolveBridgeProxy handle=h:ff60f418:237 shape=...ImportTimelineFromFile>
    Created Timeline: 'CutPilot_Imported_FCP7_01' (Track 1 Items: 3)
      Item 1: 'test-15s.mp4 · Intro: app demo start' Start=0 End=105 Duration=105
      Item 2: 'test-15s.mp4 · Action: toggle airplane mode' Start=120 End=255 Duration=135
      Item 3: 'test-15s.mp4 · Summary: worker UI' Start=270 End=375 Duration=105
    ```
- **Critical Rules for xmeml v4 Import in Resolve**:
  1. `<pathurl>` must be formatted as `file://localhost/<absolute_posix_path>`.
  2. Sequence `<name>` and import option `timelineName` must be **unique** in the project; repeating an existing timeline name causes silent failure (returns `None`).
  3. If media is already imported into the MediaPool, `importSourceClips` must be set to `False` to prevent modal relink dialogs.

---

## 6. Compatibility Claims & System Environment Verification

### Actual Machine Hardware vs. Previous Claims:
- **Previous Claim**: "Qualcomm Snapdragon X Elite (ARM64)"
- **Actual Hardware Verified via WMI (`Win32_Processor`)**:
  - **Processor**: `Snapdragon(R) X2 Plus - X2P42100 - Qualcomm Oryon(TM) CPU`
  - **Architecture**: ARMv8 (64-bit) Family 8 Model 2 Revision 101
  - **Core Count**: 6 Cores @ up to 4.03 GHz
- **Operating System**: Windows 11 Build 26100 (ARM64)
- **DaVinci Resolve**: DaVinci Resolve Free 21.0.3.7 (Build 7)
- **Python**: Native ARM64 Python 3.11.9 (`PATH`) + Isolated x64 Python 3.11.9 (`%LOCALAPPDATA%\Programs\Python\Python311-x64`) for Fusion `fuscript.exe`.

Documentation (`README.md`, `final_test_report.md`, `architecture.md`) must be updated to accurately state **Snapdragon X2 Plus**.

---

## 7. Test Suite Categorization & Verification

The test suite currently contains **21 automated tests** across unit and integration categories.

### 7.1 Pure Unit Tests (Isolated, Zero Resolve Dependency, Execution Time < 0.2s)
| Test Suite | Test Count | Scope | Result |
|---|:---:|---|:---:|
| `tests/unit/test_models.py` | 3 | Dataclass instantiation, validation, dict serialization | **PASS** |
| `tests/unit/test_validation.py` | 4 | Transcript duration bounds, edit plan sequential checks | **PASS** |
| `tests/unit/test_framerate.py` | 2 | Base framerate conversions (30 to 24, same fps) | **PASS** |
| `tests/unit/test_framerate_accuracy.py` | 5 | 72-frame canary reproduction, floor conforming, timecode offsets, half-open bounds | **PASS** |
| `tests/unit/test_captions.py` | 3 | SRT timecodes, WebVTT formatting, character/time chunking | **PASS** |
| **Total Unit Tests** | **17** | **100% In-Memory / Zero Network or Resolve** | **17/17 PASS** |

### 7.2 Mocked Integration Tests (Protocol & Tool Verification)
| Test Suite | Test Count | Scope | Result |
|---|:---:|---|:---:|
| `tests/integration/test_mcp_server.py` | 3 | MCP stdio protocol handshake, tool catalog listing, offline caption tool call | **PASS** |
| **Total Mocked Tests** | **3** | **In-Process JSON-RPC Transport** | **3/3 PASS** |

### 7.3 Live DaVinci Resolve Tests (Requires Running Bridge on `127.0.0.1:49632`)
| Test Suite | Test Count | Scope | Result |
|---|:---:|---|:---:|
| `tests/integration/test_canary_edit.py` | 1 | Live project creation, media import, timeline placement, and readback query | **PASS** (or SKIPPED if offline) |
| **Total Live Tests** | **1** | **Direct Hardware & Resolve Automation** | **1/1 PASS** |

### Execution Summary:
- **Total Executed Tests**: **21 passed in 1.37 seconds**.
- **Live Script Verifications**:
  - `python scripts/verify_bridge.py`: **PASS** (read-only project inspection).
  - `python scripts/run_canary.py`: **PASS** (verified timeline placement and readback).
