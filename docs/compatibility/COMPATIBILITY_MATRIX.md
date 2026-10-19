# CutPilot — System Requirements & Compatibility Matrix

This document defines the supported operating systems, CPU architectures, software dependencies, and testing baselines for CutPilot.

---

## 1. Compatibility Tier Definitions

CutPilot strictly distinguishes four tiers of platform compatibility:

| Tier | Definition | Verification Standard |
|---|---|---|
| **Tier 1: Supported & Tested** | Formally verified and continuously tested on physical hardware. | Full test suite passes; live canary timeline edits verified against DaVinci Resolve. |
| **Tier 2: Supported & Untested** | Fully designed, implemented, and architecturally supported, but not continuously tested on reference CI hardware. | Code is portable and tested via mocked unit suites; awaiting verified community test report. |
| **Tier 3: Experimental** | Partial or in-development support. Some capabilities or bridge calls may require platform adaptations. | Community-contributed or manual configuration required. |
| **Tier 4: Unsupported** | Known incompatible environments where core execution cannot succeed. | Not supported. |

---

## 2. Platform Compatibility Matrix

| Operating System | CPU Architecture | DaVinci Resolve Target | Tooling & Binaries | Status Tier | Notes |
|---|---|---|---|:---:|---|
| **Windows 11** | **ARM64** | DaVinci Resolve Free 21.0.3.7+ | Native ARM64 Python 3.11+, native FFmpeg & Whisper.cpp | **Supported & Tested** | Reference development testbed (Snapdragon X2 Plus). Resolve Fusion engine requires isolated x64 Python runtime launcher. |
| **Windows 10 / 11** | **x86-64 (x64)** | DaVinci Resolve Free 21.0.3+ / Studio | Standard x64 Python 3.10+, x64 FFmpeg & Whisper.cpp | **Supported & Untested** | Architecturally unified. No Python architecture mismatch between host and Fusion. |
| **macOS 13+ (Ventura+)** | **Apple Silicon (ARM64)** | DaVinci Resolve Free / Studio | Universal / ARM64 Python, Homebrew FFmpeg, Metal Whisper.cpp | **Experimental** | Loopback bridge socket protocol is cross-platform; requires mapping macOS Fusion script directory path. |
| **Linux (Ubuntu 22.04+, Fedora)** | **x86-64 (x64)** | DaVinci Resolve Studio recommended | Standard distro Python 3.10+, ffmpeg package, CPU/CUDA Whisper | **Experimental** | DaVinci Resolve Free on Linux lacks native AAC and H.264/H.265 codec support out of the box; Studio edition recommended. |
| **Windows / Linux** | **32-bit (x86)** | Any | Any | **Unsupported** | 64-bit CPU and OS required for Whisper, FFmpeg, and DaVinci Resolve. |

---

## 3. Reference Testbed Specifications

To ensure transparency, here are the factual specifications of the physical machine used to execute live DaVinci Resolve integration tests:

- **Host Device**: Snapdragon-based Windows 11 ARM64 Laptop
- **Processor**: Snapdragon(R) X2 Plus - X2P42100 - Qualcomm Oryon(TM) CPU (6 Cores @ up to 4.03 GHz)
- **Host OS**: Windows 11 Build 26100 (ARM64)
- **Primary Development Python**: Python 3.11.9 (native ARM64 on `PATH`)
- **DaVinci Resolve Version**: DaVinci Resolve Free Edition 21.0.3 Build 7
- **Resolve Fusion Scripting Host**: `fuscript.exe` (PE Machine: `0x8664` / x64)
- **Resolve Scripting Python Runtime**: Python 3.11.9 Windows x64 (installed isolated in `%LOCALAPPDATA%\Programs\Python\Python311-x64`)

> [!NOTE]
> The above hardware is an empirical development testbed. CutPilot **does not require** Snapdragon hardware and does not contain hardcoded assumptions about this processor. Any compatible Windows, macOS, or Linux system meeting the requirements below can run CutPilot.

---

## 4. General System Requirements

### 4.1 Minimum Requirements
- **Operating System**: Windows 10/11 (64-bit), macOS 13+, or modern Linux (64-bit)
- **Python**: Python 3.10 or Python 3.11 (64-bit)
- **DaVinci Resolve**: Free Edition 21.0.3 or Studio Edition 19.x/20.x/21.x
- **Memory**: 8 GB RAM minimum (16 GB recommended for Whisper models and multi-track video editing)
- **Disk**: 500 MB for CutPilot packages and tools + media storage space

### 4.2 Multi-Architecture Binary Resolution
CutPilot inspects executable binary headers (`MZ/PE`, `ELF`, `Mach-O`) at runtime to ensure process architecture compatibility:
- On **native x64 systems**, x64 binaries are selected from system `PATH` or `resources/bin/windows-x64/`.
- On **native ARM64 systems**, native ARM64 binaries are selected to avoid translation overhead.
- When cross-architecture execution is required (such as DaVinci Resolve Free's x64 Fusion engine on Windows ARM64), CutPilot relies on process-level environment isolation (`scripts/launch_resolve.bat`) rather than modifying system-wide environment variables.

---

## 5. Setting Up DaVinci Resolve Scripting Bridge

Because DaVinci Resolve Free disables external direct scripting API calls, CutPilot communicates through an authenticated loopback socket bridge running inside Resolve's internal Fusion console.

### Setup Steps:
1. Ensure DaVinci Resolve is installed.
2. Install the bridge script to your Resolve Fusion Scripts folder:
   - **Windows**: `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Comp\`
   - **macOS**: `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/`
   - **Linux**: `~/.local/share/DaVinciResolve/Fusion/Scripts/Comp/`
3. Launch DaVinci Resolve.
4. From the top menu: **Workspace → Scripts → resolve_bridge**.
5. The console will display:
   ```text
   DaVinci Resolve MCP - in-app bridge
   listening: 127.0.0.1:49632
   ```
6. Run the CutPilot verification check:
   ```powershell
   python scripts/verify_bridge.py
   ```
