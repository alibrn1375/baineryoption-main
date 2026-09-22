"""Configuration management system for the FO-X 5M Quantitative Engine.

Combines Pydantic Settings, environment variable overrides, and YAML configuration
to provide an immutable, validated, and type-safe configuration interface.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.exceptions import ConfigurationError


class AppSettings(BaseModel):
    """General application metadata and operational mode."""
    name: str = Field(default="FO-X 5M Quantitative Engine", description="Application Name")
    environment: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=False, description="Debug mode flag")
    version: str = Field(default="1.0.0", description="Configuration schema version")


class LoggingSettings(BaseModel):
    """Structured logging configuration."""
    level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    format: str = Field(default="structured", description="Format: structured or standard")
    log_to_file: bool = Field(default=True, description="Enable disk file logging")
    log_file_path: str = Field(default="logs/fox5m.log", description="Path to main log file")
    rotation: str = Field(default="100 MB", description="Log file rotation policy")
    retention: str = Field(default="30 days", description="Log retention policy")


class DatabaseSettings(BaseModel):
    """Database and timeseries cache connection."""
    db_type: str = Field(default="duckdb", description="Database backend (duckdb, parquet, etc.)")
    db_path: str = Field(default="database/fox5m.duckdb", description="DuckDB file path")
    auto_vacuum: bool = Field(default=True, description="Auto optimize database storage")


class DataSettings(BaseModel):
    """Data storage paths and processing constraints."""
    default_symbol: str = Field(default="GC_FUT", description="Primary traded instrument")
    tick_data_path: str = Field(default="data/ticks", description="Directory for historical tick data")
    parquet_cache_path: str = Field(default="data/cache", description="Directory for cached parquet bars")
    enable_validation: bool = Field(default=True, description="Strict validation on incoming ticks")
    max_memory_mb: int = Field(default=4096, description="Memory ceiling for analytics buffers")


class ResearchSettings(BaseModel):
    """Quantitative research and time-horizon parameters."""
    base_timeframe: str = Field(default="5m", description="Primary decision timeframe")
    timezone: str = Field(default="UTC", description="Reference operational timezone")
    strict_validation: bool = Field(default=True, description="Enforce strict lookahead bias validation")


class SystemConfig(BaseSettings):
    """Master configuration root aggregating sub-configurations."""
    app: AppSettings = Field(default_factory=AppSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    data: DataSettings = Field(default_factory=DataSettings)
    research: ResearchSettings = Field(default_factory=ResearchSettings)

    model_config = SettingsConfigDict(
        env_prefix="FOX_",
        env_nested_delimiter="__",
        extra="ignore"
    )

    @classmethod
    def load_from_yaml(cls, yaml_path: Optional[str] = None) -> "SystemConfig":
        """Load configuration from a YAML file with fallback to defaults."""
        target_path = yaml_path or os.getenv("FOX_CONFIG_PATH", "configs/base_config.yaml")
        path_obj = Path(target_path)

        config_dict: Dict[str, Any] = {}
        if path_obj.exists() and path_obj.is_file():
            try:
                with open(path_obj, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                    if isinstance(loaded, dict):
                        config_dict = loaded
            except Exception as e:
                raise ConfigurationError(f"Failed to parse YAML configuration at {target_path}: {e}") from e

        return cls(**config_dict)


# Global singleton instance loaded at startup
_config_instance: Optional[SystemConfig] = None


def get_config(reload: bool = False, custom_yaml_path: Optional[str] = None) -> SystemConfig:
    """Retrieve the global SystemConfig singleton instance."""
    global _config_instance
    if _config_instance is None or reload:
        _config_instance = SystemConfig.load_from_yaml(custom_yaml_path)
    return _config_instance
