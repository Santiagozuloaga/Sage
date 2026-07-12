"""
Agent Integration Interface

Abstract interface for external agent integration with SAGE Runtime.
This module defines the contract for external agents (Jules, Devin, OpenHands, Manus)
to interact with the SAGE Runtime without modifying core architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AgentCapability(Enum):
    """Agent capabilities."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    DEPLOYMENT = "deployment"


class AgentStatus(Enum):
    """Agent status."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class AgentTask:
    """Task assigned to an external agent."""
    task_id: str
    task_type: str
    description: str
    context: Dict[str, Any]
    requirements: List[str]
    priority: str
    created_at: datetime
    deadline: Optional[datetime] = None


@dataclass
class AgentResult:
    """Result from an external agent."""
    task_id: str
    agent_id: str
    success: bool
    output: Any
    metadata: Dict[str, Any]
    completed_at: datetime
    error: Optional[str] = None


class ExternalAgent(ABC):
    """
    Abstract interface for external agent integration.
    
    External agents (Jules, Devin, OpenHands, Manus) must implement
    this interface to integrate with SAGE Runtime.
    """

    @abstractmethod
    def get_agent_id(self) -> str:
        """Get unique agent identifier."""
        pass

    @abstractmethod
    def get_agent_name(self) -> str:
        """Get human-readable agent name."""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[AgentCapability]:
        """Get list of agent capabilities."""
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the agent with configuration.
        
        Args:
            config: Agent-specific configuration
            
        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    async def execute_task(self, task: AgentTask) -> AgentResult:
        """
        Execute a task assigned to the agent.
        
        Args:
            task: Task to execute
            
        Returns:
            AgentResult with execution outcome
        """
        pass

    @abstractmethod
    async def get_status(self) -> AgentStatus:
        """Get current agent status."""
        pass

    @abstractmethod
    async def shutdown(self) -> bool:
        """
        Shutdown the agent gracefully.
        
        Returns:
            True if shutdown successful
        """
        pass

    @abstractmethod
    def supports_capability(self, capability: AgentCapability) -> bool:
        """Check if agent supports a specific capability."""
        pass


class AgentIntegrationManager:
    """
    Manager for external agent integration.
    
    This component handles registration, task delegation,
    and result aggregation for external agents.
    """

    def __init__(self):
        self._registered_agents: Dict[str, ExternalAgent] = {}
        self._active_tasks: Dict[str, AgentTask] = {}
        self._task_results: Dict[str, AgentResult] = {}

    def register_agent(self, agent: ExternalAgent) -> bool:
        """
        Register an external agent.
        
        Args:
            agent: External agent instance
            
        Returns:
            True if registration successful
        """
        agent_id = agent.get_agent_id()
        if agent_id in self._registered_agents:
            return False
        
        self._registered_agents[agent_id] = agent
        return True

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an external agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if unregistration successful
        """
        if agent_id not in self._registered_agents:
            return False
        
        del self._registered_agents[agent_id]
        return True

    def get_agent(self, agent_id: str) -> Optional[ExternalAgent]:
        """Get registered agent by ID."""
        return self._registered_agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents with their capabilities."""
        agents = []
        for agent in self._registered_agents.values():
            agents.append({
                "id": agent.get_agent_id(),
                "name": agent.get_agent_name(),
                "capabilities": [cap.value for cap in agent.get_capabilities()]
            })
        return agents

    def find_agents_for_capability(self, capability: AgentCapability) -> List[ExternalAgent]:
        """Find agents that support a specific capability."""
        return [
            agent for agent in self._registered_agents.values()
            if agent.supports_capability(capability)
        ]

    async def delegate_task(
        self,
        task: AgentTask,
        agent_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Delegate a task to an agent.
        
        Args:
            task: Task to delegate
            agent_id: Specific agent ID (optional, auto-selects if None)
            
        Returns:
            Task ID if delegation successful
        """
        if agent_id:
            agent = self.get_agent(agent_id)
            if not agent:
                return None
        else:
            # Auto-select agent based on task type
            # This is a placeholder for intelligent selection logic
            agents = list(self._registered_agents.values())
            if not agents:
                return None
            agent = agents[0]  # Simple selection for now
        
        self._active_tasks[task.task_id] = task
        return task.task_id

    async def get_task_result(self, task_id: str) -> Optional[AgentResult]:
        """Get result for a completed task."""
        return self._task_results.get(task_id)

    async def shutdown_all(self) -> bool:
        """Shutdown all registered agents."""
        for agent in self._registered_agents.values():
            await agent.shutdown()
        self._registered_agents.clear()
        return True
