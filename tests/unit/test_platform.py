"""
Unit Tests for Cross-Platform Detection, Binary Architecture Inspection, and Portability
Tests mocked environments across Windows x64, Windows ARM64, macOS Apple Silicon, and Linux.
"""
from pathlib import Path
import pytest
from packages.core.platform import (
    PlatformInfo,
    SupportTier,
    get_platform_support_matrix,
    inspect_binary_architecture,
    validate_binary_compatibility,
)
from packages.core.config import Settings

class TestPlatformDetection:
    def test_windows_arm64_detection(self):
        p = PlatformInfo(system="Windows", machine="ARM64")
        assert p.system == "windows"
        assert p.cpu_arch == "arm64"
        assert p.platform_slug == "windows-arm64"
        assert p.can_emulate_x64() is True

    def test_windows_x64_detection(self):
        p = PlatformInfo(system="Windows", machine="AMD64")
        assert p.system == "windows"
        assert p.cpu_arch == "x64"
        assert p.platform_slug == "windows-x64"
        assert p.can_emulate_x64() is False

    def test_macos_apple_silicon_detection(self):
        p = PlatformInfo(system="Darwin", machine="arm64")
        assert p.system == "darwin"
        assert p.cpu_arch == "arm64"
        assert p.platform_slug == "darwin-arm64"
        assert p.can_emulate_x64() is True

    def test_linux_x64_detection(self):
        p = PlatformInfo(system="Linux", machine="x86_64")
        assert p.system == "linux"
        assert p.cpu_arch == "x64"
        assert p.platform_slug == "linux-x64"
        assert p.can_emulate_x64() is False

    def test_support_matrix_tiers(self):
        matrix = get_platform_support_matrix()
        assert "windows-arm64" in matrix
        assert matrix["windows-arm64"]["tier"] == SupportTier.SUPPORTED_TESTED
        
        assert "windows-x64" in matrix
        assert matrix["windows-x64"]["tier"] == SupportTier.SUPPORTED_UNTESTED
        
        assert "darwin-arm64" in matrix
        assert matrix["darwin-arm64"]["tier"] == SupportTier.EXPERIMENTAL
        
        assert "linux-x64" in matrix
        assert matrix["linux-x64"]["tier"] == SupportTier.EXPERIMENTAL

class TestBinaryArchitectureAndCompatibility:
    def test_inspect_real_arm64_binary(self):
        ffmpeg_bin = Path("resources/bin/windows-arm64/ffmpeg/ffmpeg.exe")
        if ffmpeg_bin.is_file():
            arch = inspect_binary_architecture(ffmpeg_bin)
            assert arch == "arm64"

    def test_binary_compatibility_on_native_host(self):
        ffmpeg_bin = Path("resources/bin/windows-arm64/ffmpeg/ffmpeg.exe")
        if ffmpeg_bin.is_file():
            host_arm64 = PlatformInfo(system="Windows", machine="ARM64")
            ok, msg = validate_binary_compatibility(ffmpeg_bin, host_arm64)
            assert ok is True
            assert "Native arm64 binary" in msg

    def test_binary_incompatibility_rejection(self):
        ffmpeg_bin = Path("resources/bin/windows-arm64/ffmpeg/ffmpeg.exe")
        if ffmpeg_bin.is_file():
            # A Linux x64 host cannot execute Windows ARM64 PE binary
            host_linux = PlatformInfo(system="Linux", machine="x86_64")
            ok, msg = validate_binary_compatibility(ffmpeg_bin, host_linux)
            assert ok is False
            assert "Incompatible" in msg

    def test_nonexistent_binary_validation(self, tmp_path):
        fake_bin = tmp_path / "nonexistent.exe"
        ok, msg = validate_binary_compatibility(fake_bin)
        assert ok is False
        assert "not found" in msg

class TestMockedConfigResolution:
    def test_settings_resolves_mocked_platform_bin_dir(self):
        mock_platform = PlatformInfo(system="Darwin", machine="arm64")
        mock_settings = Settings(platform_info=mock_platform)
        assert mock_settings.platform_bin_dir.name == "darwin-arm64"
        assert mock_settings.ffmpeg_bin_dir.parent.name == "darwin-arm64"

    def test_custom_environment_variable_override(self, tmp_path, monkeypatch):
        custom_ffmpeg = tmp_path / "custom_ffmpeg.exe"
        custom_ffmpeg.write_bytes(b"dummy")
        monkeypatch.setenv("CUTPILOT_FFMPEG_PATH", str(custom_ffmpeg))
        
        mock_settings = Settings()
        assert mock_settings.ffmpeg_path == custom_ffmpeg
