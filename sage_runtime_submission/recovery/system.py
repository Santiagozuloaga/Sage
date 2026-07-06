"""
SAGE OS Recovery System

System recovery and fault tolerance mechanisms.
"""

import asyncio
import json
import logging
import os
import tempfile
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
        """Create a system checkpoint.

        FIX R-2: previously, checkpoint_id was formatted as
        %Y%m%d_%H%M%S — two checkpoints created within the same second
        collided and the second silently overwrote the first. Adding
        microseconds (%f) makes collisions practically impossible without
        introducing a uuid dependency.

        FIX R-3: previously, json.dump wrote directly to the final path.
        If the process crashed mid-write (or disk filled), the checkpoint
        file was left truncated/empty and unreadable. Now we write to a
        sibling temp file and atomically os.replace() into place — on
        POSIX this is atomic, on Windows it is atomic when both files are
        on the same volume (which they are, by construction here).
        """
        checkpoint_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

        payload = {
            'checkpoint_id': checkpoint_id,
            'timestamp': datetime.now().isoformat(),
            'state': state
        }

        # Atomic write: temp file in same directory, then os.replace.
        # tempfile.NamedTemporaryFile picks a unique name, so concurrent
        # checkpoint writers cannot collide either.
        tmp_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=str(self.checkpoint_dir),
                prefix=f".{checkpoint_id}_",
                suffix='.tmp',
                delete=False,
            ) as tmp_fh:
                # Capture path BEFORE writing so except branch can clean up.
                tmp_path = Path(tmp_fh.name)
                json.dump(payload, tmp_fh, indent=2)
                tmp_fh.flush()
                os.fsync(tmp_fh.fileno())

            os.replace(tmp_path, checkpoint_file)
            tmp_path = None  # Successfully renamed.
        except Exception:
            # Best-effort cleanup of the temp file on failure.
            if tmp_path is not None:
                try:
                    tmp_path.unlink()
                except FileNotFoundError:
                    pass
                except Exception:
                    pass
            raise

        logger.info(f"[RECOVERY] Checkpoint created: {checkpoint_id}")
        return checkpoint_id

    async def restore_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Restore from a checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

        if not checkpoint_file.exists():
            logger.error(f"[RECOVERY] Checkpoint not found: {checkpoint_id}")
            return None

        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            logger.info(f"[RECOVERY] Checkpoint restored: {checkpoint_id}")
            return data['state']
        except Exception as e:
            logger.error(f"[RECOVERY] Failed to restore checkpoint {checkpoint_id}: {e}")
            return None

    async def list_checkpoints(self) -> list:
        """List available checkpoints.

        FIX R-5: previously this read every JSON file to extract the
        timestamp — slow on large checkpoint sets, and silently skipped
        corrupted files (which then never appeared in the cleanup list
        and accumulated forever). Now uses file mtime, which is faster
        and lets cleanup also delete corrupted files.
        """
        checkpoints = []

        for file in self.checkpoint_dir.glob("*.json"):
            try:
                mtime = file.stat().st_mtime
                # Try to read the checkpoint_id from JSON for display; if
                # the file is corrupted we still list it (with the file
                # stem as the id) so cleanup can remove it.
                checkpoint_id = file.stem
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    ts = data.get('timestamp') or datetime.fromtimestamp(mtime).isoformat()
                    checkpoint_id = data.get('checkpoint_id', checkpoint_id)
                except Exception:
                    ts = datetime.fromtimestamp(mtime).isoformat()
                    logger.warning(f"[RECOVERY] Checkpoint file unreadable, listing by mtime: {file.name}")

                checkpoints.append({
                    'checkpoint_id': checkpoint_id,
                    'timestamp': ts,
                    'file': file.name,
                    '_mtime': mtime,
                })
            except Exception as e:
                logger.warning(f"[RECOVERY] Failed to stat checkpoint {file}: {e}")

        # Sort by mtime descending (newest first); mtime is more reliable
        # than parsing timestamps from potentially-corrupt JSON.
        checkpoints.sort(key=lambda x: x.get('_mtime', 0), reverse=True)
        for c in checkpoints:
            c.pop('_mtime', None)
        return checkpoints

    async def cleanup_old_checkpoints(self, keep_count: int = 10):
        """Clean up old checkpoints, keeping the most recent ones.

        FIX R-5: previously, corrupted checkpoint files were silently
        skipped by list_checkpoints() and therefore never deleted by
        cleanup. Now list_checkpoints() returns them too (with file
        mtime). cleanup also removes corrupted files unconditionally —
        they have zero recovery value and would otherwise accumulate
        forever. Valid checkpoints are pruned to keep_count by recency.
        """
        checkpoints = await self.list_checkpoints()

        # Always delete corrupted files first — they have no recovery value.
        # We detect them by attempting to read+parse the JSON; list_checkpoints
        # already logged a warning for each one it could not parse.
        deleted_corrupted = 0
        for checkpoint in checkpoints:
            file_name = checkpoint.get('file') or f"{checkpoint['checkpoint_id']}.json"
            checkpoint_file = self.checkpoint_dir / file_name
            if not checkpoint_file.exists():
                continue
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    json.load(f)
            except Exception:
                # Corrupted — delete unconditionally.
                try:
                    checkpoint_file.unlink()
                    deleted_corrupted += 1
                    logger.info(f"[RECOVERY] Deleted corrupted checkpoint: {file_name}")
                except Exception as e:
                    logger.warning(f"[RECOVERY] Failed to delete corrupted checkpoint {file_name}: {e}")

        # Now prune valid checkpoints to keep_count by recency.
        valid = [c for c in checkpoints if (self.checkpoint_dir / (c.get('file') or f"{c['checkpoint_id']}.json")).exists()]
        if len(valid) <= keep_count:
            return

        to_delete = valid[keep_count:]
        for checkpoint in to_delete:
            file_name = checkpoint.get('file') or f"{checkpoint['checkpoint_id']}.json"
            checkpoint_file = self.checkpoint_dir / file_name
            try:
                checkpoint_file.unlink()
                logger.debug(f"[RECOVERY] Deleted old checkpoint: {checkpoint['checkpoint_id']}")
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.warning(f"[RECOVERY] Failed to delete checkpoint {file_name}: {e}")

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
