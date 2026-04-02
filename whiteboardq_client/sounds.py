"""Sound playback manager for message notification alerts."""

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect


class SoundManager:
    """Manages sound playback for notifications."""

    def __init__(self):
        self._sounds: dict[str, QSoundEffect] = {}
        self._muted = False
        self._sounds_dir = self._get_sounds_dir()
        # Sound file assignments (filename or empty string for none)
        self._sound_files = {
            "new_message": "",
            "yellow": "",
            "red": "",
            "overdue": "",
        }
        # Keep reference to preview sound to prevent garbage collection
        self._preview_sound: QSoundEffect | None = None

    @staticmethod
    def _get_sounds_dir() -> Path:
        """Get the sounds directory path."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_path = Path(sys._MEIPASS) / "whiteboardq_client"
        else:
            # Running as script
            base_path = Path(__file__).parent
        return base_path / "sounds"

    def get_available_sounds(self) -> list[str]:
        """Get list of available sound files."""
        if not self._sounds_dir.exists():
            return []
        return sorted([f.name for f in self._sounds_dir.glob("*.wav")])

    def set_muted(self, muted: bool) -> None:
        """Mute or unmute all sounds."""
        self._muted = muted

    def set_sound_file(self, sound_type: str, filename: str) -> None:
        """Set the sound file for a given sound type."""
        if sound_type in self._sound_files:
            self._sound_files[sound_type] = filename
            # Pre-load the sound effect
            if filename:
                self._load_sound(sound_type, filename)

    def _load_sound(self, sound_type: str, filename: str) -> None:
        """Load a sound effect for a given type."""
        sound_path = self._sounds_dir / filename
        if sound_path.exists():
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(sound_path)))
            effect.setVolume(0.7)
            self._sounds[sound_type] = effect
        elif sound_type in self._sounds:
            del self._sounds[sound_type]

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

    def play_new_message(self) -> None:
        """Play new message sound."""
        self._play("new_message")

    def play_yellow_warning(self) -> None:
        """Play yellow warning sound."""
        self._play("yellow")

    def play_red_warning(self) -> None:
        """Play red warning sound."""
        self._play("red")

    def play_overdue_alert(self) -> None:
        """Play overdue alert sound."""
        self._play("overdue")

    def _play(self, sound_type: str) -> None:
        """Play a sound by type."""
        if self._muted:
            return

        # Load on demand if not already loaded
        filename = self._sound_files.get(sound_type, "")
        if filename and sound_type not in self._sounds:
            self._load_sound(sound_type, filename)

        sound = self._sounds.get(sound_type)
        if sound:
            sound.play()
