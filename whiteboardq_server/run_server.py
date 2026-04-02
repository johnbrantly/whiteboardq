#!/usr/bin/env python
"""Entry point for WhiteboardQ Server executable."""

import sys


def main() -> int:
    """Main entry point."""
    # Use absolute import for PyInstaller compatibility
    from whiteboardq_server.main import main as server_main
    server_main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
