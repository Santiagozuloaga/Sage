"""
Audit data models for SAGE OS Integrity Auditor.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class AuditSeverity(Enum):
    """Audit issue severity."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditIssue:
    """An audit issue found during integrity check."""
    issue_id: str
    severity: AuditSeverity
    component: str
    description: str
    timestamp: datetime
    suggested_fix: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'issue_id': self.issue_id,
            'severity': self.severity.value,
            'component': self.component,
            'description': self.description,
            'timestamp': self.timestamp.isoformat(),
            'suggested_fix': self.suggested_fix,
            'metadata': self.metadata or {}
        }


@dataclass
class AuditReport:
    """Complete audit report."""
    report_id: str
    timestamp: datetime
    issues: List[AuditIssue]
    summary: Dict[str, Any]
    passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id,
            'timestamp': self.timestamp.isoformat(),
            'issues': [issue.to_dict() for issue in self.issues],
            'summary': self.summary,
            'passed': self.passed
        }
