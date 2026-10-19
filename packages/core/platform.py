"""
CutPilot Cross-Platform Runtime & Architecture Diagnostics
Handles OS detection, CPU architecture identification, binary compatibility inspection,
and platform support classification without hardcoding machine-specific assumptions.
"""
from __future__ import annotations

import os
import platform
import struct
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

class SupportTier(str, Enum):
    SUPPORTED_TESTED = "supported_tested"        # Verified on physical hardware
    SUPPORTED_UNTESTED = "supported_untested"    # Architecture supported, awaits live test
    EXPERIMENTAL = "experimental"                # Work in progress / community supported
    UNSUPPORTED = "unsupported"                  # Known incompatible / not supported

class PlatformInfo:
    """Encapsulates system OS and architecture attributes."""
    def __init__(
        self,
        system: Optional[str] = None,
        machine: Optional[str] = None,
        python_arch: Optional[str] = None,
    ) -> None:
        self.system = (system or platform.system()).lower()
        raw_machine = (machine or platform.machine()).lower()

        # Normalize CPU architecture
        if raw_machine in ("arm64", "aarch64"):
            self.cpu_arch = "arm64"
        elif raw_machine in ("amd64", "x86_64", "x64"):
            self.cpu_arch = "x64"
        elif raw_machine in ("x86", "i386", "i686"):
            self.cpu_arch = "x86"
        else:
            self.cpu_arch = raw_machine

        # Normalize Python interpreter architecture
        if python_arch:
            self.python_arch = python_arch
        else:
            is_64 = sys.maxsize > 2**32
            if self.cpu_arch == "arm64" and is_64:
                self.python_arch = "arm64"
            elif is_64:
                self.python_arch = "x64"
            else:
                self.python_arch = "x86"

    @property
    def platform_slug(self) -> str:
        """Returns standard slug format: {os}-{arch}, e.g. windows-arm64, windows-x64, darwin-arm64."""
        return f"{self.system}-{self.cpu_arch}"

    def can_emulate_x64(self) -> bool:
        """Windows 11 ARM64 and macOS Apple Silicon can run x64 binaries via emulation."""
        if self.system == "windows" and self.cpu_arch == "arm64":
            return True
        if self.system == "darwin" and self.cpu_arch == "arm64":
            return True
        return False

def get_platform_info() -> PlatformInfo:
    return PlatformInfo()

def inspect_binary_architecture(file_path: Path) -> str:
    """
    Inspects executable header to determine native binary CPU architecture.
    Supports Windows PE (.exe / .dll), Linux ELF, and macOS Mach-O.
    """
    p = Path(file_path)
    if not p.is_file():
        return "not_found"

    try:
        with open(p, "rb") as f:
            header = f.read(4)
            if len(header) < 4:
                return "unknown"

            # 1. Windows PE Binary (starts with 'MZ')
            if header[:2] == b"MZ":
                f.seek(0x3C)
                pe_ptr_bytes = f.read(4)
                if len(pe_ptr_bytes) < 4:
                    return "unknown"
                pe_offset = struct.unpack("<I", pe_ptr_bytes)[0]
                f.seek(pe_offset)
                pe_sig = f.read(4)
                if pe_sig != b"PE\x00\x00":
                    return "invalid_pe"
                machine_bytes = f.read(2)
                if len(machine_bytes) < 2:
                    return "unknown"
                machine = struct.unpack("<H", machine_bytes)[0]
                if machine == 0xAA64:
                    return "arm64"
                elif machine == 0x8664:
                    return "x64"
                elif machine == 0x014C:
                    return "x86"
                return f"pe_unknown_0x{machine:04x}"

            # 2. Linux ELF Binary
            elif header == b"\x7fELF":
                f.seek(18)  # e_machine offset in ELF header
                e_machine_bytes = f.read(2)
                if len(e_machine_bytes) == 2:
                    # Endianness from byte 5 (1=LE, 2=BE)
                    f.seek(5)
                    endian = "<" if f.read(1) == b"\x01" else ">"
                    e_machine = struct.unpack(f"{endian}H", e_machine_bytes)[0]
                    if e_machine == 0xB7:
                        return "arm64"
                    elif e_machine == 0x3E:
                        return "x64"
                    elif e_machine == 0x03:
                        return "x86"
                return "elf_other"

            # 3. macOS Mach-O Binary
            elif header in (b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe"):
                # Mach-O magic numbers
                cputype_bytes = f.read(4)
                if len(cputype_bytes) == 4:
                    cputype = struct.unpack("<I", cputype_bytes)[0]
                    if cputype == 0x0100000C:  # CPU_TYPE_ARM64
                        return "arm64"
                    elif cputype == 0x01000007:  # CPU_TYPE_X86_64
                        return "x64"
                return "macho_other"

            elif header in (b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"):
                return "universal_fat"

    except Exception:
        return "unreadable"

    return "unknown"

def validate_binary_compatibility(
    binary_path: Path,
    host_platform: Optional[PlatformInfo] = None,
) -> Tuple[bool, str]:
    """
    Validates whether a binary is compatible with the host system.
    Returns (is_compatible, diagnostic_message).
    """
    if not host_platform:
        host_platform = get_platform_info()

    p = Path(binary_path)
    if not p.is_file():
        return False, f"Binary not found at {p}"

    bin_arch = inspect_binary_architecture(p)
    if bin_arch == host_platform.cpu_arch:
        return True, f"Native {bin_arch} binary matches host CPU architecture."

    if host_platform.can_emulate_x64() and bin_arch == "x64":
        return True, f"x64 binary supported via OS emulation on {host_platform.platform_slug} host."

    if bin_arch == "universal_fat":
        return True, "Universal / Fat binary contains multi-architecture slices."

    return False, f"Incompatible architecture: binary is {bin_arch}, host is {host_platform.platform_slug}."

def get_platform_support_matrix() -> Dict[str, Dict[str, Any]]:
    """
    Returns factual support tier mapping for different OS and architecture configurations.
    Distinguishes Supported & Tested, Supported & Untested, Experimental, and Unsupported.
    """
    return {
        "windows-arm64": {
            "tier": SupportTier.SUPPORTED_TESTED,
            "description": "Windows 11 ARM64 (Snapdragon / Qualcomm Oryon)",
            "davinci_resolve": "Free 21.0.3+ verified via loopback bridge. Fusion requires x64 Python launcher.",
            "ffmpeg": "Native ARM64 binaries bundled in resources/bin/windows-arm64/ffmpeg.",
            "whisper": "Native ARM64 whisper-cli bundled in resources/bin/windows-arm64/whisper.",
            "notes": "Verified live on reference Snapdragon X2 Plus testbed.",
        },
        "windows-x64": {
            "tier": SupportTier.SUPPORTED_UNTESTED,
            "description": "Windows 10/11 x86-64 (Intel Core / AMD Ryzen)",
            "davinci_resolve": "Free 21.0.3+ / Studio. Standard x64 Python bridge.",
            "ffmpeg": "Standard x64 FFmpeg supported via system PATH or CUTPILOT_FFMPEG_PATH.",
            "whisper": "x64 whisper-cli supported via system PATH or CUTPILOT_WHISPER_PATH.",
            "notes": "Architecturally fully supported; requires user-supplied x64 binaries.",
        },
        "darwin-arm64": {
            "tier": SupportTier.EXPERIMENTAL,
            "description": "macOS 13+ Apple Silicon (M1/M2/M3/M4)",
            "davinci_resolve": "DaVinci Resolve Free / Studio. In-app bridge requires macOS Fusion script path.",
            "ffmpeg": "Supported via Homebrew (brew install ffmpeg).",
            "whisper": "whisper.cpp supported with Metal GPU acceleration.",
            "notes": "Experimental. In-app bridge path mapping requires macOS adaptation.",
        },
        "linux-x64": {
            "tier": SupportTier.EXPERIMENTAL,
            "description": "Linux x86-64 (Ubuntu 22.04+, Fedora)",
            "davinci_resolve": "DaVinci Resolve Studio recommended (Free on Linux has AAC/H.264 restrictions).",
            "ffmpeg": "Supported via distro package manager (apt/dnf).",
            "whisper": "whisper.cpp supported via standard compile or CUDA/Vulkan.",
            "notes": "Experimental. Linux audio codec limitations in Resolve Free apply.",
        },
    }
