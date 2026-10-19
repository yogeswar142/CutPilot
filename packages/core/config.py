"""
CutPilot Core Configuration
Central settings, directory discovery, binary resolution, and environment variables.
Provides architecture-aware executable discovery without hardcoding user or machine paths.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple

from packages.core.platform import PlatformInfo, get_platform_info, validate_binary_compatibility

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings:
    def __init__(self, platform_info: Optional[PlatformInfo] = None) -> None:
        self.project_root: Path = PROJECT_ROOT
        self.platform: PlatformInfo = platform_info or get_platform_info()
        
        # Package directories
        self.packages_dir: Path = self.project_root / "packages"
        self.resources_dir: Path = self.project_root / "resources"
        self.tests_dir: Path = self.project_root / "tests"
        self.docs_dir: Path = self.project_root / "docs"
        self.scripts_dir: Path = self.project_root / "scripts"
        self.artifacts_dir: Path = self.project_root / "artifacts"
        self.archive_dir: Path = self.project_root / "archive"
        
        # Binary & asset directories
        self.bin_dir: Path = self.resources_dir / "bin"
        self.platform_bin_dir: Path = self.bin_dir / self.platform.platform_slug
        self.ffmpeg_bin_dir: Path = self.platform_bin_dir / "ffmpeg"
        self.whisper_bin_dir: Path = self.platform_bin_dir / "whisper"
        self.models_dir: Path = self.resources_dir / "models"
        self.templates_dir: Path = self.resources_dir / "templates"
        self.fixtures_dir: Path = self.tests_dir / "fixtures"
        
        # Environment variables & overrides
        self.gemini_api_key: Optional[str] = os.environ.get("GEMINI_API_KEY")
        self.resolve_bridge_host: str = os.environ.get("DAVINCI_RESOLVE_BRIDGE_HOST", "127.0.0.1")
        self.resolve_bridge_port: int = int(os.environ.get("DAVINCI_RESOLVE_BRIDGE_PORT", "49632"))
        self.resolve_bridge_enabled: bool = os.environ.get("DAVINCI_RESOLVE_BRIDGE", "1") == "1"

    def _resolve_binary(
        self,
        env_vars: list[str],
        bundled_subpath: Path,
        system_cmd: str,
    ) -> Path:
        """
        Resolves an executable in priority order:
        1. Explicit environment variable overrides
        2. Platform-specific bundled binary under resources/bin/{platform_slug}/
        3. System PATH executable discovered via shutil.which()
        4. Fallback command name
        """
        # 1. Environment variables
        for var in env_vars:
            custom = os.environ.get(var)
            if custom:
                cp = Path(custom)
                if not cp.is_absolute():
                    cp = self.project_root / cp
                if cp.is_file():
                    return cp

        # 2. Bundled platform binary
        ext = ".exe" if self.platform.system == "windows" else ""
        bundled = bundled_subpath.with_name(bundled_subpath.name + ext) if ext and not bundled_subpath.name.endswith(ext) else bundled_subpath
        if bundled.is_file():
            return bundled

        # 3. System PATH search
        which_path = shutil.which(system_cmd)
        if which_path:
            return Path(which_path)

        return Path(system_cmd + ext if ext else system_cmd)

    @property
    def ffmpeg_path(self) -> Path:
        return self._resolve_binary(
            env_vars=["CUTPILOT_FFMPEG_PATH", "FFMPEG_BINARY"],
            bundled_subpath=self.ffmpeg_bin_dir / "ffmpeg",
            system_cmd="ffmpeg",
        )

    @property
    def ffprobe_path(self) -> Path:
        return self._resolve_binary(
            env_vars=["CUTPILOT_FFPROBE_PATH", "FFPROBE_BINARY"],
            bundled_subpath=self.ffmpeg_bin_dir / "ffprobe",
            system_cmd="ffprobe",
        )

    @property
    def whisper_cli_path(self) -> Path:
        return self._resolve_binary(
            env_vars=["CUTPILOT_WHISPER_PATH", "WHISPER_BINARY"],
            bundled_subpath=self.whisper_bin_dir / "whisper-cli",
            system_cmd="whisper-cli",
        )

    @property
    def whisper_model_path(self) -> Path:
        custom = os.environ.get("CUTPILOT_WHISPER_MODEL")
        if custom:
            cp = Path(custom)
            if not cp.is_absolute():
                cp = self.project_root / cp
            if cp.is_file():
                return cp
        bundled = self.models_dir / "whisper" / "ggml-base.bin"
        return bundled

    @property
    def canonical_test_media(self) -> Path:
        return self.fixtures_dir / "media" / "test-15s.mp4"

    def validate_setup(self) -> Dict[str, Tuple[bool, str]]:
        """Validates all configured binaries for existence and platform compatibility."""
        results = {}
        for name, path in [
            ("ffmpeg", self.ffmpeg_path),
            ("ffprobe", self.ffprobe_path),
            ("whisper-cli", self.whisper_cli_path),
        ]:
            if not path.is_file():
                results[name] = (False, f"Binary not found: {path}")
            else:
                ok, msg = validate_binary_compatibility(path, self.platform)
                results[name] = (ok, msg)
        return results

settings = Settings()
