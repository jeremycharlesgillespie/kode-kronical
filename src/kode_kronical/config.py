"""
Configuration management for KodeKronical using OmegaConf.

This module handles loading configuration from multiple sources:
1. Default configuration (config/default.yaml)
2. User configuration files (.kode-kronical.yaml, kode-kronical.yaml)
3. Runtime overrides (passed to KodeKronical constructor)

Configuration files are searched in this order:
- ./kode-kronical.yaml (current directory)
- ./.kode-kronical.yaml (current directory, hidden file)
- ~/.kode-kronical.yaml (home directory)
- ~/.config/kode-kronical/config.yaml (XDG config directory)
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from omegaconf import OmegaConf, DictConfig


logger = logging.getLogger(__name__)


class KodeKronicalConfig:
    """KodeKronical configuration manager using OmegaConf."""
    
    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration with multiple sources.
        
        Args:
            config_override: Optional runtime configuration overrides
        """
        self.config: DictConfig = self._load_config(config_override)
        self._setup_logging()
    
    def _load_config(self, config_override: Optional[Dict[str, Any]] = None) -> DictConfig:
        """Load configuration from multiple sources in priority order."""
        
        # 1. Start with default configuration
        config = self._load_default_config()
        
        # 2. Merge user configuration files
        user_config = self._load_user_config()
        if user_config:
            config = OmegaConf.merge(config, user_config)
        
        # 3. Apply runtime overrides
        if config_override:
            override_config = OmegaConf.create(config_override)
            config = OmegaConf.merge(config, override_config)
        
        # Resolve any interpolations
        config = OmegaConf.create(OmegaConf.to_yaml(config))
        
        return config
    
    def _load_default_config(self) -> DictConfig:
        """Load default configuration from default.yaml in package."""
        
        # Find the default.yaml file in the same package directory
        current_dir = Path(__file__).parent
        config_file = current_dir / "default.yaml"
        
        if not config_file.exists():
            logger.warning(f"Default config file not found: {config_file}")
            # Fallback to creating a minimal default config
            return OmegaConf.create({
                "kode_kronical": {
                    "enabled": True,
                    "debug": False,
                    "min_execution_time": 0.001,
                    "max_tracked_calls": 10000
                },
                "local": {
                    "enabled": False,
                    "data_dir": "./perf_data",
                    "format": "json",
                    "max_records": 1000
                },
                "aws": {
                    "region": "us-east-1",
                    "table_name": "kode-kronical-data",
                    "auto_create_table": True
                },
                "upload": {
                    "strategy": "on_exit"
                },
                "filters": {
                    "exclude_modules": ["boto3", "botocore", "urllib3", "requests", "logging"],
                    "include_modules": [],
                    "exclude_functions": ["^_.*", "^test_.*"],
                    "include_functions": [],
                    "track_arguments": False
                }
            })
        
        try:
            config = OmegaConf.load(config_file)
            logger.debug(f"Loaded default config from: {config_file}")
            return config
        except Exception as e:
            logger.error(f"Failed to load default config: {e}")
            return OmegaConf.create({})
    
    def _load_user_config(self) -> Optional[DictConfig]:
        """Load user configuration from various locations."""
        
        # Search locations in priority order
        search_paths = [
            Path.cwd() / "kode-kronical.yaml",            # Current directory
            Path.cwd() / ".kode-kronical.yaml",           # Current directory (hidden)
            Path.home() / ".kode-kronical.yaml",          # Home directory
            Path.home() / ".config" / "kode-kronical" / "config.yaml",  # XDG config
        ]
        
        for config_path in search_paths:
            if config_path.exists():
                try:
                    config = OmegaConf.load(config_path)
                    logger.debug(f"Loaded user config from: {config_path}")
                    return config
                except Exception as e:
                    logger.warning(f"Failed to load user config from {config_path}: {e}")
        
        return None
    
    def _setup_logging(self) -> None:
        """Setup logging based on configuration."""
        
        log_level = self.get("logging.level", "INFO")
        log_format = self.get("logging.format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        # Convert string log level to logging constant
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Configure logging
        logging.basicConfig(
            level=numeric_level,
            format=log_format,
            force=True  # Override any existing configuration
        )
        
        # Set up file logging if specified
        log_file = self.get("logging.file")
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(logging.Formatter(log_format))
            logging.getLogger().addHandler(file_handler)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'aws.region')
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        try:
            return OmegaConf.select(self.config, key, default=default)
        except Exception:
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        OmegaConf.update(self.config, key, value)
    
    def is_enabled(self) -> bool:
        """Check if KodeKronical is enabled."""
        return self.get("kode_kronical.enabled", True)
    
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get("kode_kronical.debug", False)
    
    def is_local_only(self) -> bool:
        """Check if local-only mode is enabled."""
        return self.get("local.enabled", False)
    
    def get_aws_config(self) -> Dict[str, Any]:
        """Get AWS configuration as a dictionary."""
        return OmegaConf.to_container(self.config.aws, resolve=True)
    
    def get_dashboard_config(self) -> Dict[str, Any]:
        """Get dashboard configuration as a dictionary."""
        return OmegaConf.to_container(self.config.dashboard, resolve=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entire configuration to dictionary."""
        return OmegaConf.to_container(self.config, resolve=True)
    
    def to_yaml(self) -> str:
        """Convert configuration to YAML string."""
        return OmegaConf.to_yaml(self.config)
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of issues.
        
        Returns:
            List of validation error messages
        """
        issues = []
        
        # Check if both local and AWS are disabled
        if not self.is_local_only() and not self.get("aws.region"):
            issues.append("Either local mode must be enabled or AWS region must be configured")
        
        # Validate AWS configuration if not in local mode
        if not self.is_local_only():
            if not self.get("aws.table_name"):
                issues.append("AWS table name is required when not in local mode")
        
        # Validate local configuration if in local mode
        if self.is_local_only():
            data_dir = self.get("local.data_dir")
            if not data_dir:
                issues.append("Local data directory is required in local mode")
        
        # Validate upload strategy
        valid_strategies = ["on_exit", "real_time", "batch", "manual"]
        strategy = self.get("upload.strategy")
        if strategy not in valid_strategies:
            issues.append(f"Invalid upload strategy: {strategy}. Must be one of: {valid_strategies}")
        
        # Validate minimum execution time
        min_time = self.get("kode_kronical.min_execution_time", 0.001)
        if min_time is not None and min_time < 0:
            issues.append("Minimum execution time cannot be negative")
        
        return issues


# Global configuration instance
_global_config: Optional[KodeKronicalConfig] = None


def get_config(config_override: Optional[Dict[str, Any]] = None) -> KodeKronicalConfig:
    """
    Get the global KodeKronical configuration instance.
    
    Args:
        config_override: Optional runtime configuration overrides
        
    Returns:
        KodeKronicalConfig instance
    """
    global _global_config
    
    if _global_config is None or config_override:
        _global_config = KodeKronicalConfig(config_override)
    
    return _global_config


def reload_config(config_override: Optional[Dict[str, Any]] = None) -> KodeKronicalConfig:
    """
    Reload the global configuration instance.
    
    Args:
        config_override: Optional runtime configuration overrides
        
    Returns:
        New KodeKronicalConfig instance
    """
    global _global_config
    _global_config = KodeKronicalConfig(config_override)
    return _global_config