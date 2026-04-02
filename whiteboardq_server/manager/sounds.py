"""Sound playback for Server Manager settings preview."""

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect


class SoundManager:
    """Manages sound playback for preview in settings."""

    def __init__(self):
        self._sounds_dir = self._get_sounds_dir()
        # Keep reference to preview sound to prevent garbage collection
        self._preview_sound: QSoundEffect | None = None

    @staticmethod
    def _get_sounds_dir() -> Path:
        """Get the sounds directory path."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable - sounds bundled in _MEIPASS
            return Path(sys._MEIPASS) / "whiteboardq_server" / "sounds"
        else:
            # Running as script - use client's sounds directory
            return Path(__file__).parent.parent.parent / "whiteboardq_client" / "sounds"

    def get_available_sounds(self) -> list[str]:
        """Get list of available sound files."""
        if not self._sounds_dir.exists():
            return []
        return sorted([f.name for f in self._sounds_dir.glob("*.wav")])

    def play_sound_file(self, filename: str) -> None:
        """Play a specific sound file (for preview in settings)."""
        if not filename:
            return
        sound_path = self._sounds_dir / filename
        if sound_path.exists():
            # Store reference to prevent garbage collection before playback completes
            self._preview_sound = QSoundEffect()
            self._preview_sound.setSource(QUrl.fromLocalFile(str(sound_path)))
            self._preview_sound.setVolume(0.7)
            self._preview_sound.play()
