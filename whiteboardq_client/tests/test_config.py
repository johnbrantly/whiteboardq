import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from whiteboardq_client.config import ClientConfig


class TestClientConfig:
    """Tests for ClientConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ClientConfig()
        assert config.server_host == "localhost"
        assert config.server_port == 5000
        assert config.station_name == ""
        assert config.verify_ssl is False
        assert config.disclaimer_acknowledged is False
        assert config.setup_completed is False
        assert config.theme == "light"
        assert config.always_on_top is True
        assert config.confirm_delete is True
        assert config.sound_muted is False
        assert config.sound_new_message == ""
        assert config.sound_yellow == "soft.wav"
        assert config.sound_red == "chimes.wav"
        assert config.sound_overdue == "littletrumpet.wav"
        assert config.yellow_threshold_minutes == 10
        assert config.red_threshold_minutes == 20
        assert config.overdue_threshold_minutes == 30

    def test_server_url_property(self):
        """Test server_url is computed from host and port."""
        config = ClientConfig()
        assert config.server_url == "wss://localhost:5000"

        config.server_host = "192.168.1.100"
        config.server_port = 8080
        assert config.server_url == "wss://192.168.1.100:8080"

    def test_get_default_station_name(self):
        """Test auto-detect station name."""
        name = ClientConfig.get_default_station_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_save_and_load(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"

            # Create and save config
            config = ClientConfig()
            config.station_name = "Test-Station"
            config.server_host = "192.168.1.100"
            config.server_port = 5000
            config.theme = "light"
            config.always_on_top = False
            config.confirm_delete = False
            config.disclaimer_acknowledged = True
            config.setup_completed = True

            with patch.object(ClientConfig, 'config_path', return_value=config_path):
                config.save()

                # Verify file was created
                assert config_path.exists()

                # Load and verify
                loaded = ClientConfig.load()
                assert loaded.station_name == "Test-Station"
                assert loaded.server_host == "192.168.1.100"
                assert loaded.server_port == 5000
                assert loaded.server_url == "wss://192.168.1.100:5000"
                assert loaded.theme == "light"
                assert loaded.always_on_top is False
                assert loaded.confirm_delete is False
                assert loaded.disclaimer_acknowledged is True
                assert loaded.setup_completed is True

    def test_load_missing_file(self):
        """Test loading with missing config file returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.json"

            with patch.object(ClientConfig, 'config_path', return_value=config_path):
                config = ClientConfig.load()
                assert config.theme == "light"
                assert config.server_host == "localhost"
                assert config.server_port == 5000

    def test_load_invalid_json(self):
        """Test loading with invalid JSON returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"
            config_path.write_text("not valid json")

            with patch.object(ClientConfig, 'config_path', return_value=config_path):
                config = ClientConfig.load()
                assert config.theme == "light"

    def test_partial_config(self):
        """Test loading config with only some values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"
            config_path.write_text(json.dumps({
                "station_name": "Custom-Station",
                "server_host": "10.0.0.50",
                "theme": "light"
            }))

            with patch.object(ClientConfig, 'config_path', return_value=config_path):
                config = ClientConfig.load()
                assert config.station_name == "Custom-Station"
                assert config.server_host == "10.0.0.50"
                assert config.theme == "light"
                # Defaults for unset values
                assert config.server_port == 5000
                assert config.confirm_delete is True

    def test_creates_directory(self):
        """Test that save creates the config directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "subdir" / "settings.json"

            with patch.object(ClientConfig, 'config_path', return_value=config_path):
                config = ClientConfig()
                config.save()

                assert config_path.exists()
                assert config_path.parent.exists()

    def test_effective_station_name(self):
        """Test get_effective_station_name uses hostname when not set."""
        config = ClientConfig()
        config.station_name = ""
        effective = config.get_effective_station_name()
        assert effective == ClientConfig.get_default_station_name()

        config.station_name = "Custom-Name"
        assert config.get_effective_station_name() == "Custom-Name"

    def test_restorable_defaults(self):
        """Test get_restorable_defaults returns expected values."""
        defaults = ClientConfig.get_restorable_defaults()
        assert defaults["server_host"] == "localhost"
        assert defaults["server_port"] == 5000
        assert defaults["theme"] == "light"
        assert defaults["always_on_top"] is True
        assert defaults["yellow_threshold_minutes"] == 10
        assert defaults["red_threshold_minutes"] == 20
        assert defaults["overdue_threshold_minutes"] == 30

    def test_threshold_fields(self):
        """Test threshold fields save and load correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"

            config = ClientConfig()
            config.yellow_threshold_minutes = 5
            config.red_threshold_minutes = 15
            config.overdue_threshold_minutes = 25

            with patch.object(ClientConfig, 'config_path', return_value=config_path):
                config.save()
                loaded = ClientConfig.load()

                assert loaded.yellow_threshold_minutes == 5
                assert loaded.red_threshold_minutes == 15
                assert loaded.overdue_threshold_minutes == 25
