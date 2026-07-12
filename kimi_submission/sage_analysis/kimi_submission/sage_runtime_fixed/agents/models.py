"""
Agent data models for SAGE OS Agent Router.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class AgentType(Enum):
    """Types of agents supported by SAGE OS."""
    SAGE = "sage"
    JULES = "jules"
    ANTIGRAVITY = "antigravity"
    CASCADE = "cascade"
    DEVIN = "devin"
    GEMINI = "gemini"
    CURSOR = "cursor"
    CODEX = "codex"
    CLINE = "cline"
    VS_CODE = "vs_code"
    COPILOT = "copilot"
    PERPLEXITY = "perplexity"
    LOCAL_OLLAMA = "local_ollama"
    CUSTOM = "custom"


class AgentCapability(Enum):
    """Agent capabilities."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    RESEARCH = "research"
    WEB_AUTOMATION = "web_automation"
    DATA_ANALYSIS = "data_analysis"
    VOICE_INTERFACE = "voice_interface"
    MULTI_LANGUAGE = "multi_language"


@dataclass
class Agent:
    """An agent definition."""
    agent_id: str
    agent_type: AgentType
    name: str
    description: str
    capabilities: List[AgentCapability]
    enabled: bool = True
    config: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type.value,
            'name': self.name,
            'description': self.description,
            'capabilities': [c.value for c in self.capabilities],
            'enabled': self.enabled,
            'config': self.config or {},
            'metadata': self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Agent':
        return cls(
            agent_id=data['agent_id'],
            agent_type=AgentType(data['agent_type']),
            name=data['name'],
            description=data['description'],
            capabilities=[AgentCapability(c) for c in data['capabilities']],
            enabled=data.get('enabled', True),
            config=data.get('config'),
            metadata=data.get('metadata')
        )
