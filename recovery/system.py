"""
SAGE OS Recovery System

System recovery and fault tolerance mechanisms.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


logger = logging.getLogger(__name__)


class RecoverySystem:
    """
    Recovery System for SAGE OS.
    
    Provides fault tolerance, crash recovery,
    and system state restoration capabilities.
    """

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.checkpoint_dir = config_dir / "checkpoints"
        self._initialized = False
        self._auto_recovery_enabled = True

    async def initialize(self):
        """Initialize the recovery system."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True
        logger.info("[RECOVERY] System initialized")

    async def create_checkpoint(self, state: Dict[str, Any]) -> str:
        """Create a system checkpoint."""
        checkpoint_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        
        # Save state to checkpoint file
        import json
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump({
                'checkpoint_id': checkpoint_id,
                'timestamp': datetime.now().isoformat(),
                'state': state
            }, f, indent=2)
        
        logger.info(f"[RECOVERY] Checkpoint created: {checkpoint_id}")
        return checkpoint_id

    async def restore_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Restore from a checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        
        if not checkpoint_file.exists():
            logger.error(f"[RECOVERY] Checkpoint not found: {checkpoint_id}")
            return None
        
        try:
            import json
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"[RECOVERY] Checkpoint restored: {checkpoint_id}")
            return data['state']
        except Exception as e:
            logger.error(f"[RECOVERY] Failed to restore checkpoint: {e}")
            return None

    async def list_checkpoints(self) -> list:
        """List available checkpoints."""
        checkpoints = []
        
        for file in self.checkpoint_dir.glob("*.json"):
            try:
                import json
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                checkpoints.append({
                    'checkpoint_id': data['checkpoint_id'],
                    'timestamp': data['timestamp']
                })
            except Exception as e:
                logger.warning(f"[RECOVERY] Failed to read checkpoint {file}: {e}")
        
        checkpoints.sort(key=lambda x: x['timestamp'], reverse=True)
        return checkpoints

    async def cleanup_old_checkpoints(self, keep_count: int = 10):
        """Clean up old checkpoints, keeping the most recent ones."""
        checkpoints = await self.list_checkpoints()
        
        if len(checkpoints) <= keep_count:
            return
        
        to_delete = checkpoints[keep_count:]
        for checkpoint in to_delete:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint['checkpoint_id']}.json"
            try:
                checkpoint_file.unlink()
                logger.debug(f"[RECOVERY] Deleted old checkpoint: {checkpoint['checkpoint_id']}")
            except Exception as e:
                logger.warning(f"[RECOVERY] Failed to delete checkpoint: {e}")

    async def enable_auto_recovery(self):
        """Enable automatic recovery."""
        self._auto_recovery_enabled = True
        logger.info("[RECOVERY] Auto-recovery enabled")

    async def disable_auto_recovery(self):
        """Disable automatic recovery."""
        self._auto_recovery_enabled = False
        logger.info("[RECOVERY] Auto-recovery disabled")

    async def shutdown(self):
        """Shutdown the recovery system."""
        self._initialized = False
        logger.info("[RECOVERY] Shutdown complete")
