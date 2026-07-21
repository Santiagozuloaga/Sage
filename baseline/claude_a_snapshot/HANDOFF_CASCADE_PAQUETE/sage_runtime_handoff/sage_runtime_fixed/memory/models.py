"""
Memory data models for SAGE OS Engineering Memory.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class MemoryType(Enum):
    """Types of memory records."""
    USER_PREFERENCE = "user_preference"
    PROJECT_CONTEXT = "project_context"
    ENGINEERING_DECISION = "engineering_decision"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    RFC = "rfc"
    SESSION_SUMMARY = "session_summary"


@dataclass
class MemoryRecord:
    """A single memory record."""
    id: Optional[int]
    memory_type: MemoryType
    title: str
    content: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'memory_type': self.memory_type.value,
            'title': self.title,
            'content': self.content,
            'tags': ','.join(self.tags),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'session_id': self.session_id,
            'metadata': self.metadata or {}
        }


@dataclass
class SessionRecord:
    """A session record for recovery."""
    session_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    messages: List[Dict[str, Any]]
    context: Dict[str, Any]
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'messages': self.messages,
            'context': self.context,
            'metadata': self.metadata or {}
        }


@dataclass
class PRRecord:
    """A PR workflow record."""
    pr_id: str
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    author: str
    reviewers: List[str]
    changes: Dict[str, Any]
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pr_id': self.pr_id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'author': self.author,
            'reviewers': ','.join(self.reviewers),
            'changes': self.changes,
            'metadata': self.metadata or {}
        }
