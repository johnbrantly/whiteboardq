"""Pytest configuration for client tests.

Forces process exit after tests complete to prevent PySide6 QApplication
from holding the process open on Windows (Qt's native event dispatcher
keeps running even after quit() is called).
"""

import os


def pytest_unconfigure(config):
    """Force exit after all output and reporting complete."""
    os._exit(0)
