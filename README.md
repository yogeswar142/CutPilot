# CutPilot 🎬

**CutPilot** is an autonomous, model-independent video-editing copilot designed for automated rough-cut generation, multi-modal video analysis, and direct timeline automation in **DaVinci Resolve Free 21.0.3+ and Studio**.

CutPilot provides a modular video processing engine—from speech transcription and visual scene analysis to frame-accurate timeline assembly—exposed through a canonical **Model Context Protocol (MCP)** server for AI agent orchestration.

---

## 🌟 Key Capabilities

- **Canonical Model Context Protocol (MCP) Server**: Full JSON-RPC 2.0 stdio server (`packages/cutpilot_mcp`) providing 10 verified tools for Claude Desktop, Cursor, Antigravity, and custom agent pipelines.
- **DaVinci Resolve Bridge Adapter**: Authenticated loopback socket client (`127.0.0.1:49632`) automating DaVinci Resolve Free & Studio timelines without requiring external scripting licenses.
- **Cross-Platform Architecture Detection**: Automatically inspects host OS (Windows, macOS, Linux) and CPU architecture (ARM64, x86-64) at runtime. Validates binary compatibility using PE/ELF/Mach-O executable headers before launch.
- **Replaceable AI & Inference Backends**:
  - *Audio*: Fast on-device transcription via Whisper.cpp (CPU/ARM64 NEON/Metal/CUDA) with token-level and word-level timestamps.
  - *Vision*: Cloud multi-modal intelligence via Google Gemini Video API or offline FFmpeg scene-cut/frame-difference keyframe selectors.
- **Deterministic Frame-Accurate Conforming**:
  - Exact source-to-timeline frame rate math handling differing rates (e.g. 30.0 fps source to 24.0 fps timeline conforming with verified floor truncation).
  - Synchronized SRT and WebVTT caption generator with configurable chunking and duration limits.
  - Standard Apple Final Cut Pro 7 XML (xmeml v4) timeline generator compatible with DaVinci Resolve and Adobe Premiere Pro.
- **Zero Heavy Runtime Dependencies**: Core data models, validation, socket clients, and MCP stdio transport are implemented using Python's standard library.

---

## 📁 Repository Structure

```text
CutPilot/
├── packages/
│   ├── core/                    # Typed dataclasses, validation, platform detection
│   ├── media/                   # FFmpeg / FFprobe wrapper and audio extraction
│   ├── transcription/           # Native Whisper.cpp runner & token aggregator
│   ├── analysis/                # Gemini Video API & keyframe extraction
│   ├── editing/                 # FCP7 XML (xmeml v4), captions, plan executor
│   ├── resolve_adapter/         # Resolve bridge client, framerate math, SQLite
│   ├── cutpilot_mcp/            # Canonical Model Context Protocol (MCP) server
│   └── agents/                  # Autonomous Agent 1, Agent 2, Agent 3 workflows
│
├── resources/
│   ├── bin/                     # Platform-specific binaries (e.g. windows-arm64/)
│   ├── models/                  # Manifest & weights for Whisper models
│   └── templates/               # Caption & timeline interchange templates
│
├── tests/
│   ├── unit/                    # Fast isolated tests (models, captions, framerate, platform)
│   ├── integration/             # MCP server & protocol compliance tests
│   └── fixtures/                # Canonical test media assets & sample outputs
│
├── docs/
│   ├── architecture/            # Architecture specifications, audits & ADRs
│   ├── compatibility/           # Compatibility matrix, hardware testbeds & reports
│   └── development/             # Development guides & test execution reports
│
├── scripts/                     # Healthcheck, canary verification, and launch scripts
├── pyproject.toml               # Project configuration & pytest settings
└── .env.example                 # Environment variables template
```

---

## 🖥️ System Requirements & Compatibility

CutPilot is designed to run across multiple operating systems and architectures. Platform support is explicitly categorized:

| Tier | Configurations | Status |
|---|---|:---:|
| **Tier 1: Supported & Tested** | Windows 11 ARM64 + DaVinci Resolve Free 21.0.3.7+ | Verified on reference physical testbed |
| **Tier 2: Supported & Untested** | Windows 10/11 x64 + DaVinci Resolve Free 21.0.3+ / Studio | Architecturally supported |
| **Tier 3: Experimental** | macOS 13+ Apple Silicon (M-series); Linux x64 + Resolve Studio | In development / community supported |
| **Tier 4: Unsupported** | 32-bit operating systems; DaVinci Resolve Free on Linux | Incompatible (codec/architecture constraints) |

For complete platform details and testbed specifications, see the [Compatibility Matrix](docs/compatibility/COMPATIBILITY_MATRIX.md).

---

## 🚀 Quickstart

### 1. Prerequisites
- **Python**: Python 3.10+ (64-bit)
- **DaVinci Resolve**: DaVinci Resolve Free 21.0.3+ or DaVinci Resolve Studio 19.x/20.x/21.x
- **FFmpeg & FFprobe**: Installed on system `PATH` or placed in `resources/bin/<platform_slug>/ffmpeg/`

### 2. Environment Setup

Clone the repository and copy the environment template:

```bash
git clone https://github.com/yogeswar142/CutPilot.git
cd CutPilot
cp .env.example .env
```

If you plan to use cloud multi-modal visual analysis (Agent 2), configure your API key in `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Launching DaVinci Resolve with the Bridge

To enable timeline automation in DaVinci Resolve Free:

1. Launch DaVinci Resolve.
   *(On Windows ARM64, use `scripts/launch_resolve.bat` to ensure Resolve's x64 Fusion engine finds the isolated x64 Python runtime without altering system `PATH`)*.
2. In DaVinci Resolve, open a project (e.g. `CutPilot_Canary`).
3. Open the bridge script: **Workspace → Scripts → resolve_bridge**.
   The console will display:
   ```text
   DaVinci Resolve MCP - in-app bridge
   listening: 127.0.0.1:49632
   ```

### 4. Verify Connection

Run the read-only bridge verification healthcheck:

```bash
python scripts/verify_bridge.py
```

Expected output:
```text
Connecting to DaVinci Resolve in-app bridge at 127.0.0.1:49632...
[PASS] Connected successfully!
Active Project: 'CutPilot_Canary'
Timeline Count in 'CutPilot_Canary': 1
```

---

## 🔌 Model Context Protocol (`cutpilot-mcp`)

CutPilot includes a full stdio Model Context Protocol (MCP) server conforming to the MCP 2024-11-05 JSON-RPC specification.

### Launching the Server
```bash
python -m packages.cutpilot_mcp.server
```

### Client Configuration (Claude Desktop, Cursor, Antigravity)

Add CutPilot to your client's MCP configuration file (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cutpilot": {
      "command": "python",
      "args": ["-m", "packages.cutpilot_mcp.server"],
      "cwd": "/path/to/CutPilot"
    }
  }
}
```

### Available MCP Tools

| Tool Name | Type | Description |
|---|:---:|---|
| `cutpilot_inspect_project` | Read-only | Returns active project name, frame rate, resolution, and project list. |
| `cutpilot_inspect_timeline` | Read-only | Returns tracks, clip details, durations, and playhead position. |
| `cutpilot_create_project` | Write | Creates and loads a new project in the project library. |
| `cutpilot_import_media` | Write | Imports a media asset into the active project's Media Pool. |
| `cutpilot_create_timeline` | Write | Creates a new timeline with a given name in the active project. |
| `cutpilot_place_clip` | Write | Inserts a media pool clip onto a specific track with frame bounds. |
| `cutpilot_verify_timeline` | Read-only | Verifies clip existence, start frame, and duration on a timeline. |
| `cutpilot_generate_captions`| Utility | Formats word timestamps into valid `.srt` or `.vtt` subtitles. |
| `cutpilot_export_fcp7xml` | Utility | Generates Apple Final Cut Pro 7 XML (xmeml v4) interchange file. |
| `cutpilot_export_fcpxml` | Utility | Alias for `cutpilot_export_fcp7xml` (xmeml v4). |

---

## 🧪 Testing & Verification

CutPilot includes a layered test suite with distinct execution tiers:

```bash
# Run all unit tests (isolated, fast, zero network or Resolve dependency)
pytest tests/unit

# Run full test suite
pytest

# Run live canary editing verification against DaVinci Resolve
python scripts/run_canary.py
```

### Test Suite Highlights:
- **`tests/unit/test_platform.py`**: OS detection, architecture normalization, PE/ELF/Mach-O header inspection, and compatibility validation across mocked Windows ARM64/x64, macOS, and Linux environments.
- **`tests/unit/test_framerate_accuracy.py`**: Frame rate translation math, floor truncation conforming ($72 / 30 = 2.4\text{s} \times 24 = 57.6 \to 57 \text{ frames}$), inclusive/exclusive bounds, and start timecode offsets (`86400`).
- **`tests/unit/test_models.py`**: Schema serialization and validation for media assets and edit plans.
- **`tests/unit/test_captions.py`**: SRT and WebVTT subtitle formatting and word-chunking rules.
- **`tests/integration/test_mcp_server.py`**: MCP JSON-RPC protocol compliance, tool catalog listing, and offline dispatch.

---

## 🛡️ Safety & Conforming Invariants

1. **Explicit Project Confirmation**: Write operations strictly require active project confirmation. Automation scripts abort if the open project does not match the expected target.
2. **Project Isolation**: Production projects are protected. Integration tests and canary scripts target disposable test projects (`CutPilot_Canary`).
3. **Local Loopback Security**: The bridge binds exclusively to `127.0.0.1` using HMAC-SHA256 authentication derived from local configuration.
4. **Frame Rate Normalization**: Clip bounds are converted using mathematically sound frame rate ratios with floor conforming to eliminate silent drift across mixed frame-rate media.

---

## 📜 Attribution & License

CutPilot is licensed under the **[MIT License](LICENSE)**.

This project adapts and refactors ideas from open-source projects under their respective MIT licenses:
- **`davinci-resolve-mcp`** by Samuel Gursky ([License](packages/resolve_adapter/THIRD_PARTY_LICENSES/LICENSE-davinci-resolve-mcp)): In-app loopback bridge protocol, socket client, and Resolve Free compatibility discovery.
- **`videopowers`** by Vinit Agarwal ([License](packages/editing/THIRD_PARTY_LICENSES/LICENSE-videopowers)): Final Cut Pro 7 XML (xmeml v4) timeline structure and captions generation logic.
