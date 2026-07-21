"""
SAGE OS Configuration Manager

Centralized configuration management for the runtime.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Configuration Manager for SAGE OS.
    
    Manages runtime configuration, user preferences,
    and system settings.
    """

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_file = config_dir / "config.json"
        self.config: Dict[str, Any] = {}

    async def load(self) -> Dict[str, Any]:
        """Load configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"[CONFIG] Loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"[CONFIG] Failed to load: {e}")
                self.config = self._default_config()
        else:
            self.config = self._default_config()
            await self.save()
        
        return self.config

    async def save(self) -> bool:
        """Save configuration."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"[CONFIG] Saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"[CONFIG] Failed to save: {e}")
            return False

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
        self.config[key] = value
        return True

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration."""
        return self.config.copy()
