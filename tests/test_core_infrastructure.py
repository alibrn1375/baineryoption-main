"""Tests for FO-X 5M configuration and logging infrastructure."""

import os
from app.core.config import SystemConfig, get_config
from app.core.logging import log_event, app_logger


def test_system_config_defaults() -> None:
    config = SystemConfig()
    assert config.app.name == "FO-X 5M Quantitative Engine"
    assert config.app.environment == "development"
    assert config.research.base_timeframe == "5m"
    assert config.data.default_symbol == "GC_FUT"


def test_system_config_singleton() -> None:
    cfg1 = get_config()
    cfg2 = get_config()
    assert cfg1 is cfg2


def test_structured_event_logging() -> None:
    # Ensure logging does not raise exceptions
    log_event(
        event_type="TEST_EVENT",
        message="Running unit test validation",
        payload={"symbol": "GC_FUT", "test_passed": True},
        level="INFO"
    )
    assert app_logger is not None
