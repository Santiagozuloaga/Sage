"""
Contract data models for SAGE OS Contract Validator.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class ContractStatus(Enum):
    """Contract validation status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Contract:
    """A contract defining system behavior or requirements."""
    contract_id: str
    title: str
    description: str
    status: ContractStatus
    created_at: datetime
    updated_at: datetime
    author: str
    reviewers: List[str]
    content: Dict[str, Any]
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'contract_id': self.contract_id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'author': self.author,
            'reviewers': self.reviewers,
            'content': self.content,
            'metadata': self.metadata or {}
        }


@dataclass
class RFC:
    """Request for Comments document."""
    rfc_id: str
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    author: str
    discussion: List[Dict[str, Any]]
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rfc_id': self.rfc_id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'author': self.author,
            'discussion': self.discussion,
            'metadata': self.metadata or {}
        }
