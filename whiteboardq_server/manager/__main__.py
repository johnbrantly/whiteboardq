"""Allow running as: python -m whiteboardq_server.manager

For development, this defaults to FrontDesk mode.
In production, use the separate executables:
- WhiteboardQ-FrontDesk-Manager.exe
- WhiteboardQ-BackOffice-Manager.exe
"""

from .main_frontdesk import main

if __name__ == "__main__":
    main()
