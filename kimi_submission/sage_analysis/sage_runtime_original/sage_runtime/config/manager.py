"""
SAGE OS Configuration Manager

Centralized configuration management for the runtime.
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Union


logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Configuration Manager for SAGE OS.
    
    Manages runtime configuration, user preferences,
    and system settings with atomic writes and validation.
    """

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_file = config_dir / "config.json"
        self.config: Dict[str, Any] = {}
        self._locked_keys = {"session_id", "boot_timestamp"}  # Keys that cannot be modified

    async def load(self) -> Dict[str, Any]:
        """Load configuration with error recovery."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                
                # Validate config structure
                self._validate_config()
                logger.info(f"[CONFIG] Loaded from {self.config_file}")
            except json.JSONDecodeError as e:
                logger.error(f"[CONFIG] JSON decode error: {e}, using defaults")
                self.config = self._default_config()
                await self._backup_corrupted_config()
            except Exception as e:
                logger.error(f"[CONFIG] Failed to load: {e}, using defaults")
                self.config = self._default_config()
        else:
            self.config = self._default_config()
            await self.save()
        
        # Ensure all default keys exist
        self._merge_defaults()
        
        return self.config

    async def save(self) -> bool:
        """Save configuration with atomic write."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Atomic write: write to temp file then rename
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=self.config_dir,
                prefix='.config_tmp_',
                suffix='.json',
                delete=False,
                encoding='utf-8'
            ) as tmp_file:
                json.dump(self.config, tmp_file, indent=2)
                tmp_path = Path(tmp_file.name)
            
            # Atomic rename
            tmp_path.replace(self.config_file)
            logger.info(f"[CONFIG] Saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"[CONFIG] Failed to save: {e}")
            return False

    def _validate_config(self):
        """Validate configuration structure."""
        if not isinstance(self.config, dict):
            raise ValueError("Configuration must be a dictionary")
        
        # Validate known keys have correct types
        type_validations = {
            "model": str,
            "max_tokens": int,
            "permission_mode": str,
            "max_tool_output": int,
            "max_agent_depth": int,
            "max_concurrent_agents": int,
            "language": str,
            "personality": str
        }
        
        for key, expected_type in type_validations.items():
            if key in self.config and not isinstance(self.config[key], expected_type):
                logger.warning(f"[CONFIG] Invalid type for {key}, resetting to default")
                del self.config[key]

    def _merge_defaults(self):
        """Merge default values for missing keys."""
        defaults = self._default_config()
        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value

    async def _backup_corrupted_config(self):
        """Backup corrupted configuration file."""
        if self.config_file.exists():
            backup_path = self.config_file.with_suffix('.json.corrupted')
            try:
                self.config_file.rename(backup_path)
                logger.info(f"[CONFIG] Backed up corrupted config to {backup_path}")
            except Exception as e:
                logger.error(f"[CONFIG] Failed to backup corrupted config: {e}")

    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "model": "claude-sonnet-4-6",
            "max_tokens": 8192,
            "permission_mode": "auto",
            "max_tool_output": 32000,
            "max_agent_depth": 3,
            "max_concurrent_agents": 3,
            "language": "spanish",
            "personality": "sage"
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set a configuration value."""
        if key in self._locked_keys:
            logger.warning(f"[CONFIG] Cannot modify locked key: {key}")
            return False
        
        self.config[key] = value
        return True

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration."""
        return self.config.copy()

    def merge(self, updates: Dict[str, Any]) -> bool:
        """Merge configuration updates."""
        for key, value in updates.items():
            if key not in self._locked_keys:
                self.config[key] = value
        return True

    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults (preserving locked keys)."""
        locked_values = {k: self.config[k] for k in self._locked_keys if k in self.config}
        self.config = self._default_config()
        self.config.update(locked_values)
        logger.info("[CONFIG] Reset to defaults")
        return True
