#!/usr/bin/env python3
"""
WhiteboardQ Build Script

Builds all executables and copies them to the dist/ folder.

Usage:
    python build.py                    # Build all
    python build.py client             # Build client only
    python build.py server             # Build server only (standalone, for FrontDesk)
    python build.py service            # Build service only (Windows Service, for BackOffice)
    python build.py frontdesk-manager  # Build FrontDesk Manager (tray + subprocess)
    python build.py backoffice-manager # Build BackOffice Manager (no tray, service control)

Outputs:
    dist/WhiteboardQ.exe                   - Desktop client
    dist/WhiteboardQ-Server.exe            - Standalone server (FrontDesk tray spawns this)
    dist/WhiteboardQ-Server-Service.exe    - Windows Service wrapper (BackOffice installs this)
    dist/WhiteboardQ-FrontDesk-Manager.exe - FrontDesk Manager GUI (tray, subprocess control)
    dist/WhiteboardQ-BackOffice-Manager.exe - BackOffice Manager GUI (no tray, service control)

Installers (built separately with Inno Setup):
    FrontDesk: Server.exe + FrontDesk-Manager.exe (tray mode spawns server as subprocess)
    BackOffice: Service.exe + BackOffice-Manager.exe (server runs as Windows Service)
"""

import shutil
import subprocess
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent
DIST_DIR = PROJECT_ROOT / "dist"
VERSION_FILE = PROJECT_ROOT / "_version_frozen.txt"


def write_frozen_version() -> str:
    """Write version from git to frozen version file for PyInstaller."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        if result.returncode == 0:
            version = result.stdout.strip().lstrip("v")
        else:
            version = "0.0.0"
    except Exception:
        version = "0.0.0"

    VERSION_FILE.write_text(version)
    print(f"Version: {version}")
    return version

BUILDS = {
    "client": {
        "name": "WhiteboardQ Client",
        "spec": PROJECT_ROOT / "whiteboardq_client" / "build.spec",
        "output": "WhiteboardQ.exe",
        "build_dir": PROJECT_ROOT / "whiteboardq_client",
    },
    "server": {
        "name": "WhiteboardQ Server",
        "spec": PROJECT_ROOT / "whiteboardq_server" / "build.spec",
        "output": "WhiteboardQ-Server.exe",
        "build_dir": PROJECT_ROOT / "whiteboardq_server",
    },
    "service": {
        "name": "WhiteboardQ Server Service",
        "spec": PROJECT_ROOT / "whiteboardq_server" / "build_service.spec",
        "output": "WhiteboardQ-Server-Service.exe",
        "build_dir": PROJECT_ROOT / "whiteboardq_server",
    },
    "frontdesk-manager": {
        "name": "WhiteboardQ FrontDesk Manager",
        "spec": PROJECT_ROOT / "whiteboardq_server" / "manager" / "build_frontdesk.spec",
        "output": "WhiteboardQ-FrontDesk-Manager.exe",
        "build_dir": PROJECT_ROOT / "whiteboardq_server" / "manager",
    },
    "backoffice-manager": {
        "name": "WhiteboardQ BackOffice Manager",
        "spec": PROJECT_ROOT / "whiteboardq_server" / "manager" / "build_backoffice.spec",
        "output": "WhiteboardQ-BackOffice-Manager.exe",
        "build_dir": PROJECT_ROOT / "whiteboardq_server" / "manager",
    },
}

# Documentation
README_SRC = PROJECT_ROOT / "docs" / "readme.txt"
README_DST = DIST_DIR / "README.txt"


def build(target: str) -> bool:
    """Build a single target."""
    config = BUILDS[target]
    print(f"\n{'='*60}")
    print(f"Building {config['name']}...")
    print(f"{'='*60}\n")

    # Run PyInstaller
    result = subprocess.run(
        ["pyinstaller", str(config["spec"]), "--noconfirm"],
        cwd=config["build_dir"],
    )

    if result.returncode != 0:
        print(f"\n[FAIL] FAILED: {config['name']}")
        return False

    # Copy to dist folder
    src = config["build_dir"] / "dist" / config["output"]
    dst = DIST_DIR / config["output"]

    if src.exists():
        DIST_DIR.mkdir(exist_ok=True)
        shutil.copy2(src, dst)
        size_mb = dst.stat().st_size / (1024 * 1024)
        print(f"\n[OK] Built: {dst} ({size_mb:.1f} MB)")
        return True
    else:
        print(f"\n[FAIL] Output not found: {src}")
        return False


def build_all() -> bool:
    """Build all targets."""
    success = True
    for target in BUILDS:
        if not build(target):
            success = False
    return success


def copy_readme() -> None:
    """Copy README from docs/ to dist/."""
    if README_SRC.exists():
        DIST_DIR.mkdir(exist_ok=True)
        shutil.copy2(README_SRC, README_DST)
        print(f"[OK] Copied README.txt to dist/")


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(BUILDS.keys())

    # Validate targets
    for target in targets:
        if target not in BUILDS:
            print(f"Unknown target: {target}")
            print(f"Available: {', '.join(BUILDS.keys())}")
            sys.exit(1)

    print("WhiteboardQ Build Script")
    print(f"Output directory: {DIST_DIR}")

    # Write frozen version file before building
    write_frozen_version()

    success = True
    for target in targets:
        if not build(target):
            success = False

    print(f"\n{'='*60}")
    if success:
        # Copy README to dist
        copy_readme()

        print("BUILD COMPLETE")
        print(f"\nExecutables in: {DIST_DIR}")
        for f in DIST_DIR.glob("*.exe"):
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  - {f.name} ({size_mb:.1f} MB)")
    else:
        print("BUILD FAILED - See errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()
