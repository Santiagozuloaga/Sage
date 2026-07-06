"""
SAGE OS Boot Configurator

System boot configuration and initialization.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import json


logger = logging.getLogger(__name__)


class BootConfigurator:
    """
    Boot Configurator for SAGE OS.
    
    Manages boot configuration, system initialization parameters,
    and boot-time validation with atomic writes and error recovery.
    """

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_file = config_dir / "boot_config.json"
        self.config: Dict[str, Any] = {}
        self._validated = False
        self._locked_keys = {"version", "boot_timestamp"}  # Keys that cannot be modified

    async def load(self) -> Dict[str, Any]:
        """Load boot configuration with error recovery."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                
                # Validate config structure
                self._validate_config()
                logger.info(f"[BOOT] Configuration loaded from {self.config_file}")
            except json.JSONDecodeError as e:
                logger.error(f"[BOOT] JSON decode error: {e}, using defaults")
                self.config = self._default_config()
                await self._backup_corrupted_config()
            except Exception as e:
                logger.error(f"[BOOT] Failed to load config: {e}, using defaults")
                self.config = self._default_config()
        else:
            self.config = self._default_config()
            await self.save()
        
        # Ensure all default keys exist
        self._merge_defaults()
        
        return self.config

    async def save(self) -> bool:
        """Save boot configuration with atomic write."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Atomic write: write to temp file then rename
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=self.config_dir,
                prefix='.boot_config_tmp_',
                suffix='.json',
                delete=False,
                encoding='utf-8'
            ) as tmp_file:
                json.dump(self.config, tmp_file, indent=2)
                tmp_path = Path(tmp_file.name)
            
            # Atomic rename
            tmp_path.replace(self.config_file)
            logger.info(f"[BOOT] Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"[BOOT] Failed to save config: {e}")
            return False

    def _validate_config(self):
        """Validate configuration structure."""
        if not isinstance(self.config, dict):
            raise ValueError("Configuration must be a dictionary")
        
        # Validate known keys have correct types
        type_validations = {
            "version": str,
            "boot_mode": str,
            "auto_checkpoint": bool,
            "checkpoint_interval": int,
            "memory_persistence": bool,
            "agent_routing": bool,
            "event_bus_enabled": bool,
            "max_concurrent_tasks": int,
            "log_level": str,
            "ui_mode": str
        }
        
        for key, expected_type in type_validations.items():
            if key in self.config and not isinstance(self.config[key], expected_type):
                logger.warning(f"[BOOT] Invalid type for {key}, resetting to default")
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
                logger.info(f"[BOOT] Backed up corrupted config to {backup_path}")
            except Exception as e:
                logger.error(f"[BOOT] Failed to backup corrupted config: {e}")

    def _default_config(self) -> Dict[str, Any]:
        """Get default boot configuration."""
        return {
            "version": "4.5",
            "boot_mode": "normal",
            "auto_checkpoint": True,
            "checkpoint_interval": 300,
            "memory_persistence": True,
            "agent_routing": True,
            "event_bus_enabled": True,
            "max_concurrent_tasks": 3,
            "default_agent": "sage_primary",
            "log_level": "INFO",
            "ui_mode": "cli"
        }

    async def validate(self) -> bool:
        """Validate boot configuration."""
        required_keys = [
            "version", "boot_mode", "auto_checkpoint", "memory_persistence",
            "agent_routing", "event_bus_enabled", "max_concurrent_tasks"
        ]
        
        for key in required_keys:
            if key not in self.config:
                logger.error(f"[BOOT] Missing required config key: {key}")
                return False
        
        self._validated = True
        logger.info("[BOOT] Configuration validated")
        return True

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set a configuration value."""
        if key in self._locked_keys:
            logger.warning(f"[BOOT] Cannot modify locked key: {key}")
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

    async def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults (preserving locked keys)."""
        locked_values = {k: self.config[k] for k in self._locked_keys if k in self.config}
        self.config = self._default_config()
        self.config.update(locked_values)
        return await self.save()
