"""
SAGE OS Configuration Manager

Centralized configuration management for the runtime.
"""

import json
import logging
import os
import tempfile
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
        """
        Load configuration.

        Merges the saved file over _default_config() rather than replacing
        it outright. Why: before this fix, an existing config.json entirely
        replaced self.config, so any default key added to _default_config()
        after a user's config.json was first created would never appear for
        them - code elsewhere calling config.get("new_key", fallback) would
        silently get `fallback` forever instead of the intended default,
        even though _default_config() says otherwise. Verified with a
        reproduction test: a config.json containing only {"model": "..."}
        loaded as exactly that single key, with no "personality"/"language"/
        etc. Confirmed fixed by the same test after this change.
        """
        defaults = self._default_config()
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                self.config = {**defaults, **saved}
                logger.info(f"[CONFIG] Loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"[CONFIG] Failed to load: {e}")
                self.config = defaults
        else:
            self.config = defaults
            await self.save()
        
        return self.config

    async def save(self) -> bool:
        """
        Save configuration atomically (write to a temp file, then rename).

        Why: the previous implementation wrote directly to config.json with
        a single open(..., 'w'). If the process is killed mid-write (crash,
        power loss, OOM-kill - all realistic on the low-RAM hardware this
        project targets), config.json is left truncated/corrupted, and the
        next load() falls back to defaults, silently discarding whatever the
        user had configured. os.replace() is atomic on both POSIX and
        Windows, so the config file is always either the old complete
        version or the new complete version, never a partial write.
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                dir=self.config_dir, prefix=".config_", suffix=".json.tmp"
            )
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2)
                os.replace(tmp_path, self.config_file)
            except Exception:
                Path(tmp_path).unlink(missing_ok=True)
                raise
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

    async def set(self, key: str, value: Any) -> bool:
        """
        Set a configuration value and persist it immediately.

        Why this is now async and calls save(): previously `set()` only
        mutated self.config in memory and returned True unconditionally,
        even though nothing was written to disk - any value set this way
        was silently lost on the next restart. Verified with a reproduction
        test: set() a key, construct a fresh ConfigManager on the same
        directory (simulating a restart), and the key was gone. There were
        zero existing callers of set() anywhere in the codebase at the time
        of this fix, so widening the signature to async is a safe change
        with no call sites to update.
        """
        self.config[key] = value
        return await self.save()

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration (shallow copy)."""
        return self.config.copy()
