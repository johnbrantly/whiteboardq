"""Entry point for WhiteboardQ FrontDesk Manager.

FrontDesk mode:
- Shows window on launch (visible, not hidden)
- Has tray icon, hides to tray on close (X button)
- Manages server as subprocess (not Windows Service)
- Auto-starts server on launch
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from whiteboardq_server.manager.single_instance import SingleInstanceGuard, bring_window_to_front


def get_program_data_dir() -> Path:
    """Get the ProgramData directory for WhiteboardQ Server.

    Per spec: %ProgramData%\\WhiteboardQ\\ contains:
    - config.json (server configuration)
    - whiteboardq.db (SQLite database)
    - logs/server.log
    """
    import os

    # Always use %ProgramData%\WhiteboardQ\ in both dev and production
    program_data = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData"))
    return program_data / "WhiteboardQ"


def get_icon_path() -> Path | None:
    """Get path to application icon."""
    if getattr(sys, "frozen", False):
        # Frozen exe - icon bundled in _MEIPASS
        icon_path = Path(sys._MEIPASS) / "whiteboardq_server" / "resources" / "icon.png"
    else:
        # Development mode
        server_icon = Path(__file__).parent.parent / "resources" / "icon.png"
        if server_icon.exists():
            return server_icon
        icon_path = Path(__file__).parent.parent.parent / "whiteboardq_client" / "resources" / "icon.png"

    return icon_path if icon_path.exists() else None


def main():
    """Main entry point for FrontDesk Manager."""
    app = QApplication(sys.argv)
    app.setApplicationName("WhiteboardQ Server Manager")

    # Keep app running when window is hidden (tray keeps it alive)
    app.setQuitOnLastWindowClosed(False)

    # Set application icon
    icon_path = get_icon_path()
    if icon_path and icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Single instance check
    guard = SingleInstanceGuard("whiteboardq-frontdesk-manager")
    if not guard.try_acquire():
        # Another instance running - it will show its window
        print("Another instance is already running. Bringing it to front.")
        return 0

    # Get paths per spec: %ProgramData%\WhiteboardQ\
    program_data_dir = get_program_data_dir()
    program_data_dir.mkdir(parents=True, exist_ok=True)

    db_file = program_data_dir / "whiteboardq.db"
    log_dir = program_data_dir / "logs"

    # Import after QApplication created
    from whiteboardq_server.manager.ui.main_window import MainWindow
    from whiteboardq_server.manager.tray import TrayManager

    # Create main window in frontdesk mode
    window = MainWindow(
        mode="frontdesk",
        db_file=db_file,
        log_dir=log_dir,
    )

    # Create tray manager (auto-starts server)
    tray_manager = TrayManager(
        log_dir=log_dir,
        auto_start_server=True,
        parent=None,
    )

    # Connect tray to window
    tray_manager.set_main_window(window)
    window.set_tray_manager(tray_manager)

    # Handle quit request from tray
    tray_manager.quit_requested.connect(app.quit)

    # Connect single instance guard to bring window to front
    guard.show_window_requested.connect(lambda: bring_window_to_front(window))

    # Show window immediately (FrontDesk shows on launch)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
