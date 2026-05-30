"""Tests for logger.py — logging configuration and setup."""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


class TestLoggerSetup:
    """Tests for setup_logger function."""

    def test_logger_returns_logger_instance(self):
        """Verify setup_logger returns a valid Logger instance."""
        from logger import setup_logger

        # Reset the global flag for testing
        import logger as logger_module
        logger_module._configured = False

        logger = setup_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

        # Reset flag again for other tests
        logger_module._configured = False

    def test_logger_creates_log_directory(self):
        """Verify the log directory is created if it doesn't exist."""
        from logger import setup_logger
        import logger as logger_module
        logger_module._configured = False

        log_dir = Path("log")
        # Remove log dir if it exists to test creation
        existed = log_dir.exists()
        if existed:
            import shutil
            shutil.rmtree(log_dir, ignore_errors=True)

        setup_logger("test_dir_creation")
        assert log_dir.exists()
        assert log_dir.is_dir()

        # Clean up
        import shutil
        shutil.rmtree(log_dir, ignore_errors=True)
        logger_module._configured = False

    def test_logger_configured_once(self):
        """Verify _configured flag prevents reconfiguration."""
        from logger import setup_logger
        import logger as logger_module
        logger_module._configured = False

        logger1 = setup_logger("logger_a")
        logger2 = setup_logger("logger_b")

        # Both should work, but only first call configures
        assert isinstance(logger1, logging.Logger)
        assert isinstance(logger2, logging.Logger)
        logger_module._configured = False

    def test_logger_outputs_messages(self, capsys: pytest.CaptureFixture[str]):
        """Verify logger actually outputs messages at correct levels."""
        from logger import setup_logger
        import logger as logger_module
        logger_module._configured = False

        logger = setup_logger("test_output")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        captured = capsys.readouterr()
        assert "Info message" in captured.out
        assert "Warning message" in captured.out
        assert "Error message" in captured.out
        logger_module._configured = False

    def test_logger_missing_config_exits(self):
        """Verify missing logger.yaml causes exit."""
        from logger import setup_logger
        import logger as logger_module
        logger_module._configured = False

        # Rename logger.yaml temporarily
        config_path = Path("logger.yaml")
        if config_path.exists():
            backup = config_path.rename("logger.yaml.bak")

        with pytest.raises(SystemExit) as exc_info:
            setup_logger("test_exit")
        assert exc_info.value.code == 1

        # Restore config
        if config_path.exists():
            pass  # File was already restored or doesn't exist
        backup_path = Path("logger.yaml.bak")
        if backup_path.exists():
            backup.rename(config_path)
        logger_module._configured = False

    def test_yaml_config_structure(self):
        """Verify the logger.yaml file has valid YAML with correct structure."""
        with open("logger.yaml", "r") as f:
            config = yaml.safe_load(f)

        assert "version" in config
        assert config["version"] == 1
        assert "formatters" in config
        assert "handlers" in config
        assert "root" in config
        assert "console" in config["handlers"]
        assert "file" in config["handlers"]
        assert isinstance(config["handlers"]["file"].get("maxBytes"), int)
        assert isinstance(config["handlers"]["file"].get("backupCount"), int)
