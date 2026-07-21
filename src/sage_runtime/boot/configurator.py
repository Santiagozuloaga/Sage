"""
SAGE OS Boot Configurator

System boot configuration and initialization.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import json


logger = logging.getLogger(__name__)


class BootConfigurator:
    """
    Boot Configurator for SAGE OS.
    
    Manages boot configuration, system initialization parameters,
    and boot-time validation.
    """

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_file = config_dir / "boot_config.json"
        self.config: Dict[str, Any] = {}
        self._validated = False

    async def load(self) -> Dict[str, Any]:
        """Load boot configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"[BOOT] Configuration loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"[BOOT] Failed to load config: {e}")
                self.config = self._default_config()
        else:
            self.config = self._default_config()
            await self.save()
        
        return self.config

    async def save(self) -> bool:
        """Save boot configuration."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"[BOOT] Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"[BOOT] Failed to save config: {e}")
            return False

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
        self.config[key] = value
        return True

    async def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults."""
        self.config = self._default_config()
        return await self.save()
