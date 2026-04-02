"""Single instance guard using Windows mutex and RegisterWindowMessage.

Ensures only one instance of the application runs at a time.
When a second instance launches, it broadcasts a message to bring the existing window to front.

This uses the standard Windows pattern that has been reliable since the 90s:
1. First instance: Create mutex, register custom window message, proceed normally
2. Second instance: Fail to acquire mutex, broadcast the message, exit
3. First instance: Receives broadcast, shows window
"""

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal, Qt, QAbstractNativeEventFilter, QByteArray
from PySide6.QtWidgets import QWidget, QApplication


# Windows API
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Constants
HWND_BROADCAST = 0xFFFF
ERROR_ALREADY_EXISTS = 183


class NativeEventFilter(QAbstractNativeEventFilter):
    """Filter to catch Windows messages in Qt's event loop."""

    def __init__(self, message_id: int, callback):
        super().__init__()
        self._message_id = message_id
        self._callback = callback

    def nativeEventFilter(self, eventType: QByteArray, message) -> tuple:
        """Filter native Windows messages."""
        if eventType == b"windows_generic_MSG":
            # message is a shiboken VoidPtr - convert to int for ctypes
            msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
            if msg.message == self._message_id:
                self._callback()
                return (True, 0)  # Message handled
        return (False, 0)  # Pass through


class MSG(ctypes.Structure):
    """Windows MSG structure."""
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class SingleInstanceGuard(QObject):
    """Ensures single instance using Windows mutex and RegisterWindowMessage.

    Usage:
        guard = SingleInstanceGuard("MyApp")
        if not guard.try_acquire():
            return 0  # Another instance exists, we signaled it, now exit

        guard.show_window_requested.connect(lambda: bring_window_to_front(window))
        # ... run app ...
    """

    show_window_requested = Signal()

    def __init__(self, app_id: str, parent=None):
        super().__init__(parent)
        self._app_id = app_id
        self._mutex = None
        self._message_id = 0
        self._event_filter = None

    def try_acquire(self) -> bool:
        """Try to become the primary instance.

        Returns:
            True if we are the primary instance (should continue running).
            False if another instance exists (we broadcast show message, should exit).
        """
        # Register a unique window message for this app
        message_name = f"WM_{self._app_id}_SHOW"
        self._message_id = user32.RegisterWindowMessageW(message_name)

        # Try to create a named mutex
        mutex_name = f"Local\\{self._app_id}_SingleInstance"
        self._mutex = kernel32.CreateMutexW(None, False, mutex_name)
        last_error = kernel32.GetLastError()

        if last_error == ERROR_ALREADY_EXISTS:
            # Another instance is running - broadcast show message and exit
            user32.PostMessageW(HWND_BROADCAST, self._message_id, 0, 0)
            return False

        # We are the first instance - install event filter to receive the broadcast
        self._event_filter = NativeEventFilter(
            self._message_id,
            lambda: self.show_window_requested.emit()
        )
        app = QApplication.instance()
        if app:
            app.installNativeEventFilter(self._event_filter)

        return True


def bring_window_to_front(window: QWidget) -> None:
    """Bring a window to the foreground on Windows.

    Uses Windows API to force the window to foreground, working around
    Windows' focus-stealing prevention.
    """
    # Show the window first (in case it was hidden)
    window.show()

    # Restore from minimized state if needed
    window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)

    # Get the window handle
    hwnd = int(window.winId())

    # Use AllowSetForegroundWindow to permit our process to set foreground
    # Then use SetForegroundWindow
    try:
        user32.AllowSetForegroundWindow(-1)  # ASFW_ANY = -1
        user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

    # Qt methods as backup
    window.raise_()
    window.activateWindow()
