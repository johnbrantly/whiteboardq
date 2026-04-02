"""
WhiteboardQ Version Module

Provides version info from git tags via setuptools-scm.
Works in three modes:
1. Frozen (PyInstaller) - reads from _version_frozen.txt
2. Installed package - uses importlib.metadata
3. Dev/direct run - falls back to git describe
"""

import re
import sys
from pathlib import Path

_version_cache = None
_full_version_cache = None


def _get_frozen_version() -> str | None:
    """Read version from frozen file (PyInstaller builds)."""
    if not getattr(sys, 'frozen', False):
        return None

    # Check for version file in executable directory
    if hasattr(sys, '_MEIPASS'):
        version_file = Path(sys._MEIPASS) / "_version_frozen.txt"
        if version_file.exists():
            return version_file.read_text().strip()

    return None


def _get_installed_version() -> str | None:
    """Read version from installed package metadata."""
    try:
        from importlib.metadata import version
        return version("whiteboardq")
    except Exception:
        return None


def _get_git_version() -> str | None:
    """Read version from git describe."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        if result.returncode == 0:
            return result.stdout.strip().lstrip("v")
    except Exception:
        pass
    return None


def get_full_version() -> str:
    """
    Get the full version string including dev/commit info.

    Examples:
        "0.9.2" (at a tag)
        "0.9.2.dev3+g1a2b3c4" (3 commits after tag)
    """
    global _full_version_cache

    if _full_version_cache is not None:
        return _full_version_cache

    # Try each source in order
    version = _get_frozen_version()
    if not version:
        version = _get_installed_version()
    if not version:
        version = _get_git_version()
    if not version:
        version = "0.0.0"

    # Strip leading 'v' if present
    version = version.lstrip("v")

    _full_version_cache = version
    return version


def get_version() -> str:
    """
    Get clean semver version for UI display.

    Strips any dev/local suffixes.
    Examples:
        "0.9.2.dev3+g1a2b3c4" -> "0.9.2"
        "0.9.2" -> "0.9.2"
    """
    global _version_cache

    if _version_cache is not None:
        return _version_cache

    full = get_full_version()

    # Extract just the x.y.z part
    match = re.match(r'^(\d+\.\d+\.\d+)', full)
    if match:
        _version_cache = match.group(1)
    else:
        # Fallback: take everything before first non-version char
        _version_cache = re.split(r'[^0-9.]', full)[0] or full

    return _version_cache
