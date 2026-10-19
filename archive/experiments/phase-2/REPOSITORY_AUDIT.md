# CutPilot Phase 2 — Repository Audit Report

**Audit Date:** October 19, 2026  
**Auditor:** Antigravity AI Engineering  
**Scope:** Evaluation of external repositories for CutPilot's editing-tool layer:
1. `samuelgursky/davinci-resolve-mcp` (v4.14.3)
2. `vinit-agr/videopowers` (Commit `main`)

---

## 1. Executive Summary

CutPilot requires a reusable, reliable, model-independent editing-tool layer capable of:
1. Reading project and media information.
2. Generating, trimming, and assembling multi-track timelines.
3. Operating safely on **DaVinci Resolve Free 21.1.1 on Windows 11 ARM64 (Qualcomm Snapdragon X2 Plus)** without requiring Studio licenses, system-level security compromises, or untrusted drivers.

Our empirical audit reveals that while `samuelgursky/davinci-resolve-mcp` offers deep coverage for Resolve Studio, its direct execution pathways are hard-gated by Blackmagic Design on DaVinci Resolve Free 21.1+. Conversely, `vinit-agr/videopowers` demonstrates a robust, production-tested **FCPXML (`xmeml v4`) timeline generation architecture** that bypasses all scripting restrictions and imports cleanly into Resolve Free.

Combined with CutPilot's discovery of non-destructive **Direct Read-Only SQLite Inspection of `Project.db`**, CutPilot can achieve full read-and-write editing tool capabilities on Resolve Free 21.1.1.

---

## 2. Comprehensive Audit: `samuelgursky/davinci-resolve-mcp`

- **Repository:** `https://github.com/samuelgursky/davinci-resolve-mcp`
- **Current Version:** `4.14.3`
- **License:** MIT License (Copyright (c) 2024-2026 Samuel Gursky)
- **Primary Language:** Python 3.10+ & TypeScript / Node.js
- **Declared Target:** DaVinci Resolve Studio 18.5 – 21.0+ (macOS, Windows, Linux)

### 2.1 Architecture & Design
`davinci-resolve-mcp` is designed as a full-featured Model Context Protocol (MCP) server providing LLMs with comprehensive control over DaVinci Resolve.

1. **Dual Tool Interfaces:**
   - **37 Compound Tools:** Ergonomic high-level workflows (e.g., `inspect_timeline`, `apply_edits`, `grade_shot`, `export_deliverable`).
   - **390 Granular Tools:** Low-level 1:1 bindings to the DaVinci Resolve Python Scripting API (`Resolve`, `ProjectManager`, `Project`, `MediaPool`, `Timeline`, `TimelineItem`, etc.).
2. **Monolithic Backend Core:**
   - `src/server.py` is an extensive 1.6 MB script implementing tool schemas, action dispatchers, parameter validators, and security guards.
3. **Transport Layer:**
   - **Local Studio Scripting:** Uses Blackmagic's C-extension loader `DaVinciResolveScript.py` and `fusionscript.dll` (`dvr_script.scriptapp("Resolve")`).
   - **Network Studio Scripting:** Connects to remote Resolve Studio instances via `RESOLVE_SCRIPT_HOST`.
   - **In-App Bridge (`resolve_bridge.py`):** An embedded HTTP server running on `127.0.0.1:49632` designed to run inside Resolve's GUI process, bypassing the external process block on older Free editions (Resolve 18.5 – 21.0.x).

### 2.2 Dependencies & Prerequisites
- **Python:** 3.10 to 3.14 (requires `psutil`, `requests`, `websockets`).
- **Node.js:** v18+ for the MCP client/server runner.
- **DaVinci Resolve License:** Strictly requires **DaVinci Resolve Studio** for external scripting API access.

### 2.3 Critical Limitations on DaVinci Resolve Free 21.1+
1. **External Process Block:** Blackmagic strictly gates `scriptapp("Resolve")` to Studio. Calling this on Resolve Free returns `None`.
2. **In-App Python Scripting Removal:** Starting in DaVinci Resolve Free 21.1 (confirmed in upstream issue `#203` and documented in `resolve_bridge_canary.lua`), Blackmagic removed Python script enumeration from the **Workspace ▸ Scripts** menu. Only `.lua` scripts are enumerated. As a result, the Python bridge server cannot be launched from within Resolve Free 21.1+.
3. **Heavy Studio Bloat:** Substantial portions of the repository focus on Studio-only features: DRX live panel grading calibration, Fairlight audio buses, Dolby Vision, HDR10+, DCTL encryption, and multi-cam normalizers. These add unnecessary complexity for CutPilot's rough-cut workflow.

---

## 3. Comprehensive Audit: `vinit-agr/videopowers`

- **Repository:** `https://github.com/vinit-agr/videopowers`
- **Current Version:** Commit `main`
- **License:** MIT License (Copyright (c) 2026 Vinit Agarwal)
- **Primary Language:** TypeScript (Node.js/Bun) & Python
- **Declared Target:** YouTube Video Creation Factory (Claude Code, DaVinci Resolve, Remotion, FFmpeg)

### 3.1 Architecture & Design
`videopowers` is modeled after unix pipelines for video creation, separating the production lifecycle into specialized skills:
1. `outline-shaping` (Planned)
2. `script-writing` (Planned)
3. `packaging-kit` (Planned)
4. `footage-rough-cut` (**Built & Battle-Tested**)
5. `mg-setup`, `mg-layout`, `mg-design` (**Built**, Remotion-based motion graphics)
6. `mg-visuals`, `mg-polish`, `mg-render` (Planned)

### 3.2 Key Reusable Components in `footage-rough-cut`
1. **FCP7 XML (`xmeml v4`) Timeline Generator (`xml.ts`):**
   - Directly converts a structured `CutPlan` (audio/video segments, trim in/out points, track indices, beat gaps) into a standard Final Cut Pro XML file (`rough-cut.xml`).
   - DaVinci Resolve Free natively imports this via `File -> Import Timeline` without requiring any scripting API or running server.
   - Preserves full trimmable clip handles so human editors can adjust edits in Resolve.
2. **EDL (Edit Decision List) Engine (`edl.ts`):**
   - Builds deterministic cut ranges from word timestamps with lead/trail audio padding buffers (`padLead`, `padTrail`) and silence merging.
3. **Resolve Append Safety Rules (`resolve-append.py`):**
   - Highlights crucial Blackmagic quirks: Playback rate must match timeline FPS exactly (mismatches cause 1.25x audio drift), batch clip insertion must be chunked (<=100 items), and `GetItemListInTrack` lies by truncating at 500 items.

### 3.3 Dependencies & Unfinished Features
- **Unfinished Skills:** 6 out of 10 skills in `videopowers` are stubs/placeholders.
- **Vendor Lock-in:** Motion graphics components tightly couple to Remotion and React.
- **External Transcription:** Uses ElevenLabs Scribe API rather than local whisper models.

---

## 4. Reusability Matrix for CutPilot

| Component / Pattern | Origin | Classification | Rationale & Recommendation for CutPilot |
|---|---|---|---|
| **FCPXML (`xmeml v4`) Generator** | `videopowers/scripts/xml.ts` | **Reuse & Adapt** | Port directly to Python in CutPilot adapter. 100% works on Resolve Free 21.1+ without API gating. |
| **Pacing & Padding Logic** | `videopowers/scripts/edl.ts` | **Reuse & Adapt** | Adopt `padLead`/`padTrail` buffering to prevent clipped speech consonants when cutting Agent 1 transcripts. |
| **Direct SQLite `Project.db` Inspection** | CutPilot Core Discovery | **Adopt as Primary Read Tool** | Enables fast, zero-dependency, read-only inspection of active projects, timelines, tracks, and media pool assets. |
| **FPS Matching & Validation** | `videopowers/scripts/resolve-append.py` | **Adopt** | Guard against project playback framerate mismatches to prevent audio/video drift. |
| **Granular API MCP Server (`server.py`)** | `davinci-resolve-mcp` | **Avoid** | 1.6 MB monolith dependent on Studio API; unusable on Resolve Free 21.1+. |
| **In-App Loopback Bridge** | `davinci-resolve-mcp/scripts/` | **Keep as External Reference / Studio Mode Only** | Keep documented for future Studio users, but do not rely on it for Free 21.1+. |
| **Remotion Motion Graphics** | `videopowers/skills/mg-*` | **Avoid** | Out of scope for CutPilot rough-cut video editing layer. |

---

## 5. Intellectual Property & Attribution Notice

All reused algorithms and schemas from `samuelgursky/davinci-resolve-mcp` and `vinit-agr/videopowers` are licensed under the MIT License. In accordance with license requirements, full copyright notices and MIT license texts are retained in CutPilot's reference tree and reflected in code header comments.
