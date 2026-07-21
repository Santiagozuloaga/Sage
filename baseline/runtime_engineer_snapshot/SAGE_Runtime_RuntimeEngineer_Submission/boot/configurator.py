"""
SAGE OS Boot Configurator

System boot configuration and initialization.
"""

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional


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
        """Save boot configuration.

        FIX B-2: previously json.dump wrote directly to the final path.
        If the process crashed mid-write (or disk filled, or another
        process was reading), the boot_config.json file was left
        truncated/empty and the next boot would fall back to defaults
        silently. Now writes to a sibling temp file and atomically
        os.replace() into place — on POSIX this is atomic, on Windows
        it is atomic when both files are on the same volume (which they
        are, by construction here).
        """
        # Pre-allocate tmp_path as None so the cleanup branch can always
        # check it, even if the failure happens before the file is opened.
        tmp_path: Optional[Path] = None
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            # tempfile.NamedTemporaryFile in the same dir guarantees same-volume
            # rename target, and a unique name avoids concurrent-save collisions.
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=str(self.config_dir),
                prefix='.boot_config_',
                suffix='.tmp',
                delete=False,
            ) as tmp_fh:
                # Capture the path BEFORE writing so the except branch can
                # clean it up even if json.dump raises mid-write.
                tmp_path = Path(tmp_fh.name)
                json.dump(self.config, tmp_fh, indent=2)
                tmp_fh.flush()
                os.fsync(tmp_fh.fileno())

            os.replace(tmp_path, self.config_file)
            tmp_path = None  # Successfully renamed — nothing to clean up.
            logger.info(f"[BOOT] Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"[BOOT] Failed to save config: {e}")
            # Best-effort cleanup of temp file on failure. tmp_path is
            # guaranteed to be set if the NamedTemporaryFile was opened.
            if tmp_path is not None:
                try:
                    tmp_path.unlink()
                except FileNotFoundError:
                    pass
                except Exception:
                    pass
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
