"""
SAGE OS Engineering Memory Engine

SQLite-based persistent memory with automatic checkpointing,
session recovery, and PR history tracking.
"""

import sqlite3
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from .models import MemoryRecord, SessionRecord, PRRecord, MemoryType


logger = logging.getLogger(__name__)


def _encode_list(items: List[str]) -> str:
    """Encode a list of strings (tags, reviewers) as JSON."""
    return json.dumps(items or [])


def _decode_list(raw: Optional[str]) -> List[str]:
    """
    Decode a list of strings previously written by _encode_list.

    Why this isn't just json.loads(raw): rows written before this fix used
    ','.join(items) / .split(','), which silently corrupts any single tag or
    reviewer name containing a comma (verified with a reproduction test:
    tag "thinking=medium, hardcoded" round-tripped as two separate tags,
    ['thinking=medium', ' hardcoded']). New writes use JSON via
    _encode_list. This falls back to comma-split only when the stored value
    isn't valid JSON, so existing databases keep working instead of losing
    data or erroring on the next read after this change ships.
    """
    if not raw:
        return []
    try:
        decoded = json.loads(raw)
        if isinstance(decoded, list):
            return decoded
    except (json.JSONDecodeError, TypeError):
        pass
    return raw.split(',')


class MemoryEngine:
    """
    Engineering Memory Engine using SQLite.
    
    Features:
    - Automatic checkpointing
    - Engineering records storage
    - Session recovery
    - PR history tracking
    - Runtime state persistence
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._checkpoint_interval = 300  # 5 minutes
        self._checkpoint_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize the database schema."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # WAL mode: without this, SQLite's default rollback-journal mode
        # blocks readers during a write. This project's own canon
        # (PATCH #07 in the Metal Sonic changelog) already calls this out
        # as a required mitigation for exactly that reason; it just was
        # never actually applied here. Verified: PRAGMA journal_mode
        # reported "delete" (SQLite's default) before this fix.
        self.conn.execute("PRAGMA journal_mode=WAL")
        await self._create_schema()
        logger.info(f"[MEMORY] Initialized at {self.db_path}")

    async def _create_schema(self):
        """Create database tables."""
        cursor = self.conn.cursor()
        
        # Memory records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                session_id TEXT,
                metadata TEXT
            )
        """)
        
        # Session records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_records (
                session_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                messages TEXT NOT NULL,
                context TEXT,
                metadata TEXT
            )
        """)
        
        # PR records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pr_records (
                pr_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                author TEXT NOT NULL,
                reviewers TEXT,
                changes TEXT,
                metadata TEXT
            )
        """)
        
        # Runtime state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runtime_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_records(memory_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_session ON memory_records(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pr_status ON pr_records(status)")
        
        self.conn.commit()

    async def save_memory(self, record: MemoryRecord) -> Optional[int]:
        """Save a memory record. Returns the record id, or None on failure."""
        try:
            cursor = self.conn.cursor()

            if record.id is None:
                cursor.execute("""
                    INSERT INTO memory_records 
                    (memory_type, title, content, tags, created_at, updated_at, session_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.memory_type.value,
                    record.title,
                    record.content,
                    _encode_list(record.tags),
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                    record.session_id,
                    json.dumps(record.metadata or {})
                ))
                record_id = cursor.lastrowid
            else:
                cursor.execute("""
                    UPDATE memory_records
                    SET memory_type=?, title=?, content=?, tags=?, updated_at=?, session_id=?, metadata=?
                    WHERE id=?
                """, (
                    record.memory_type.value,
                    record.title,
                    record.content,
                    _encode_list(record.tags),
                    record.updated_at.isoformat(),
                    record.session_id,
                    json.dumps(record.metadata or {}),
                    record.id
                ))
                record_id = record.id

            self.conn.commit()
            logger.debug(f"[MEMORY] Saved memory record: {record_id}")
            return record_id
        except sqlite3.Error as e:
            logger.error(f"[MEMORY] Failed to save memory record: {e}")
            return None

    async def get_memory(self, memory_id: int) -> Optional[MemoryRecord]:
        """Retrieve a memory record by ID."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM memory_records WHERE id=?", (memory_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_memory_record(row)
            return None
        except sqlite3.Error as e:
            logger.error(f"[MEMORY] Failed to get memory record {memory_id}: {e}")
            return None

    async def search_memories(
        self,
        memory_type: Optional[MemoryType] = None,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[MemoryRecord]:
        """Search memory records."""
        try:
            cursor = self.conn.cursor()

            sql = "SELECT * FROM memory_records WHERE 1=1"
            params = []

            if memory_type:
                sql += " AND memory_type=?"
                params.append(memory_type.value)

            if query:
                sql += " AND (title LIKE ? OR content LIKE ?)"
                params.extend([f"%{query}%", f"%{query}%"])

            if tags:
                for tag in tags:
                    sql += " AND tags LIKE ?"
                    params.append(f"%{tag}%")

            sql += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            return [self._row_to_memory_record(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"[MEMORY] Search failed: {e}")
            return []

    async def save_session(self, session: SessionRecord) -> bool:
        """Save a session record."""
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO session_records
                (session_id, started_at, ended_at, messages, context, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.started_at.isoformat(),
                session.ended_at.isoformat() if session.ended_at else None,
                json.dumps(session.messages),
                json.dumps(session.context),
                json.dumps(session.metadata or {})
            ))

            self.conn.commit()
            logger.debug(f"[MEMORY] Saved session: {session.session_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"[MEMORY] Failed to save session {session.session_id}: {e}")
            return False

    async def load_session(self, session_id: str) -> Optional[SessionRecord]:
        """Load a session record."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM session_records WHERE session_id=?", (session_id,))
            row = cursor.fetchone()

            if row:
                return SessionRecord(
                    session_id=row['session_id'],
                    started_at=datetime.fromisoformat(row['started_at']),
                    ended_at=datetime.fromisoformat(row['ended_at']) if row['ended_at'] else None,
                    messages=json.loads(row['messages']),
                    context=json.loads(row['context']) if row['context'] else {},
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
            return None
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"[MEMORY] Failed to load session {session_id}: {e}")
            return None

    async def save_pr(self, pr: PRRecord) -> bool:
        """Save a PR record."""
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO pr_records
                (pr_id, title, description, status, created_at, updated_at, author, reviewers, changes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pr.pr_id,
                pr.title,
                pr.description,
                pr.status,
                pr.created_at.isoformat(),
                pr.updated_at.isoformat(),
                pr.author,
                _encode_list(pr.reviewers),
                json.dumps(pr.changes),
                json.dumps(pr.metadata or {})
            ))

            self.conn.commit()
            logger.debug(f"[MEMORY] Saved PR: {pr.pr_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"[MEMORY] Failed to save PR {pr.pr_id}: {e}")
            return False

    async def get_pr(self, pr_id: str) -> Optional[PRRecord]:
        """Retrieve a PR record."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM pr_records WHERE pr_id=?", (pr_id,))
            row = cursor.fetchone()

            if row:
                return PRRecord(
                    pr_id=row['pr_id'],
                    title=row['title'],
                    description=row['description'],
                    status=row['status'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    author=row['author'],
                    reviewers=_decode_list(row['reviewers']),
                    changes=json.loads(row['changes']) if row['changes'] else {},
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
            return None
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"[MEMORY] Failed to get PR {pr_id}: {e}")
            return None

    async def set_runtime_state(self, key: str, value: Any) -> bool:
        """Set a runtime state value."""
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO runtime_state (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, json.dumps(value), datetime.now().isoformat()))

            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"[MEMORY] Failed to set runtime state '{key}': {e}")
            return False

    async def get_runtime_state(self, key: str) -> Optional[Any]:
        """Get a runtime state value."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT value FROM runtime_state WHERE key=?", (key,))
            row = cursor.fetchone()

            if row:
                return json.loads(row['value'])
            return None
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"[MEMORY] Failed to get runtime state '{key}': {e}")
            return None

    async def checkpoint(self):
        """Perform automatic checkpoint."""
        logger.info("[MEMORY] Checkpointing...")
        self.conn.commit()
        logger.debug("[MEMORY] Checkpoint complete")

    async def start_auto_checkpoint(self):
        """Start automatic checkpointing."""
        if self._checkpoint_task is None:
            self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())
            logger.info("[MEMORY] Auto-checkpoint started")

    async def stop_auto_checkpoint(self):
        """Stop automatic checkpointing."""
        if self._checkpoint_task:
            self._checkpoint_task.cancel()
            self._checkpoint_task = None
            logger.info("[MEMORY] Auto-checkpoint stopped")

    async def _checkpoint_loop(self):
        """Background checkpoint loop."""
        try:
            while True:
                await asyncio.sleep(self._checkpoint_interval)
                await self.checkpoint()
        except asyncio.CancelledError:
            pass

    async def shutdown(self):
        """Shutdown the memory engine."""
        await self.stop_auto_checkpoint()
        if self.conn:
            self.conn.commit()
            self.conn.close()
            logger.info("[MEMORY] Shutdown complete")

    def _row_to_memory_record(self, row: sqlite3.Row) -> MemoryRecord:
        """Convert database row to MemoryRecord."""
        return MemoryRecord(
            id=row['id'],
            memory_type=MemoryType(row['memory_type']),
            title=row['title'],
            content=row['content'],
            tags=_decode_list(row['tags']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            session_id=row['session_id'],
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )
