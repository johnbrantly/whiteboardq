"""WhiteboardQ Client - Desktop application for WhiteboardQ messaging system."""

import sys
from pathlib import Path

# Add project root to path for version import
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from version import get_version

__version__ = get_version()
