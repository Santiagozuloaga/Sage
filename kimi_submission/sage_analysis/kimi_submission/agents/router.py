"""
SAGE OS Agent Router

Multi-agent orchestration and routing system supporting future agent integration.
"""

import logging
from typing import Dict, List, Optional, Set
from pathlib import Path

from .models import Agent, AgentType, AgentCapability


logger = logging.getLogger(__name__)


class AgentRouter:
    """
    Agent Router for multi-agent orchestration.
    
    Supports:
    - SAGE, Jules, Antigravity, Cascade, Devin, Gemini, Cursor, Codex, Cline
    - VS Code, Copilot, Perplexity
    - Local Ollama agents
    - Custom agents
    
    Architecture is designed to allow future agent addition without modification.
    """

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._capability_index: Dict[AgentCapability, Set[str]] = {}
        self._type_index: Dict[AgentType, Set[str]] = {}
        # FIX A-2: Track per-agent load to enable load-aware routing.
        # Without this, route_to_agent() always returns the first matching
        # agent, potentially overloading it while other capable agents sit idle.
        self._agent_load: Dict[str, int] = {}  # agent_id -> assigned_task_count

    async def initialize(self):
        """Initialize the router with default agents."""
        await self._register_default_agents()
        logger.info("[AGENT_ROUTER] Initialized with default agents")

    async def _register_default_agents(self):
        """Register the default SAGE OS agents."""
        # SAGE - Primary coordinator
        await self.register_agent(Agent(
            agent_id="sage_primary",
            agent_type=AgentType.SAGE,
            name="SAGE",
            description="Primary SAGE OS coordinator agent",
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_REVIEW,
                AgentCapability.DEBUGGING,
                AgentCapability.ARCHITECTURE,
                AgentCapability.MULTI_LANGUAGE
            ],
            enabled=True
        ))

        # Jules - Optimization specialist
        await self.register_agent(Agent(
            agent_id="jules_optimizer",
            agent_type=AgentType.JULES,
            name="Jules",
            description="Code optimization and performance specialist",
            capabilities=[
                AgentCapability.REFACTORING,
                AgentCapability.DEBUGGING,
                AgentCapability.ARCHITECTURE
            ],
            enabled=True
        ))

        # Antigravity - Memory systems
        await self.register_agent(Agent(
            agent_id="antigravity_memory",
            agent_type=AgentType.ANTIGRAVITY,
            name="Antigravity",
            description="Memory systems and data persistence specialist",
            capabilities=[
                AgentCapability.DATA_ANALYSIS,
                AgentCapability.DEBUGGING
            ],
            enabled=True
        ))

        # Cascade - Current execution agent
        await self.register_agent(Agent(
            agent_id="cascade_executor",
            agent_type=AgentType.CASCADE,
            name="Cascade",
            description="Current execution agent (SWE-1.6)",
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_REVIEW,
                AgentCapability.DEBUGGING,
                AgentCapability.REFACTORING
            ],
            enabled=True
        ))

        # Devin - Collaboration agent
        await self.register_agent(Agent(
            agent_id="devin_collab",
            agent_type=AgentType.DEVIN,
            name="Devin",
            description="Collaboration and workflow agent",
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.TESTING,
                AgentCapability.DOCUMENTATION
            ],
            enabled=True
        ))

        # Local Ollama - Local models
        await self.register_agent(Agent(
            agent_id="ollama_local",
            agent_type=AgentType.LOCAL_OLLAMA,
            name="Local Ollama",
            description="Local model execution via Ollama",
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.MULTI_LANGUAGE
            ],
            enabled=True
        ))

        # Placeholder agents for future integration
        future_agents = [
            (AgentType.GEMINI, "Gemini", "Google Gemini integration"),
            (AgentType.CURSOR, "Cursor", "Cursor IDE agent"),
            (AgentType.CODEX, "Codex", "OpenAI Codex integration"),
            (AgentType.CLINE, "Cline", "Cline agent"),
            (AgentType.VS_CODE, "VS Code", "VS Code Copilot agent"),
            (AgentType.COPILOT, "Copilot", "GitHub Copilot integration"),
            (AgentType.PERPLEXITY, "Perplexity", "Perplexity research agent"),
        ]

        for agent_type, name, description in future_agents:
            await self.register_agent(Agent(
                agent_id=f"{agent_type.value}_placeholder",
                agent_type=agent_type,
                name=name,
                description=description,
                capabilities=[AgentCapability.CODE_GENERATION],
                enabled=False  # Disabled until integrated
            ))

    async def register_agent(self, agent: Agent) -> bool:
        """Register a new agent."""
        self._agents[agent.agent_id] = agent
        
        # Index by capabilities
        for capability in agent.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = set()
            self._capability_index[capability].add(agent.agent_id)
        
        # Index by type
        if agent.agent_type not in self._type_index:
            self._type_index[agent.agent_type] = set()
        self._type_index[agent.agent_type].add(agent.agent_id)
        
        # FIX A-2: Initialize load tracking for new agent
        self._agent_load[agent.agent_id] = 0
        
        logger.info(f"[AGENT_ROUTER] Registered agent: {agent.name} ({agent.agent_id})")
        return True

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id not in self._agents:
            return False
        
        agent = self._agents[agent_id]
        
        # Remove from capability index
        for capability in agent.capabilities:
            if capability in self._capability_index:
                self._capability_index[capability].discard(agent_id)
                # FIX A-3: Remove empty sets from the capability index.
                # Previously, empty sets accumulated forever after unregistering
                # the last agent with a given capability.
                if not self._capability_index[capability]:
                    del self._capability_index[capability]
        
        # Remove from type index
        if agent.agent_type in self._type_index:
            self._type_index[agent.agent_type].discard(agent_id)
            # FIX A-3: Also clean empty type index sets
            if not self._type_index[agent.agent_type]:
                del self._type_index[agent.agent_type]
        
        # FIX A-2: Clean up load tracking
        self._agent_load.pop(agent_id, None)
        
        del self._agents[agent_id]
        logger.info(f"[AGENT_ROUTER] Unregistered agent: {agent_id}")
        return True

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def get_agents_by_type(self, agent_type: AgentType) -> List[Agent]:
        """Get all agents of a specific type."""
        agent_ids = self._type_index.get(agent_type, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_agents_by_capability(self, capability: AgentCapability) -> List[Agent]:
        """Get all agents with a specific capability."""
        agent_ids = self._capability_index.get(capability, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_enabled_agents(self) -> List[Agent]:
        """Get all enabled agents."""
        return [agent for agent in self._agents.values() if agent.enabled]

    def route_to_agent(self, capability: AgentCapability, 
                       agent_type: Optional[AgentType] = None,
                       fallback: bool = True) -> Optional[Agent]:
        """
        Route a task to the best available agent.
        
        Priority:
        1. If agent_type specified, use enabled agent of that type with capability
        2. Otherwise, use any enabled agent with the capability
        3. Prefer least-loaded agent (FIX A-2)
        4. Prefer SAGE for coordination tasks
        
        FIX A-1: If no agent matches and fallback=True, returns the primary
        SAGE agent or any enabled agent instead of None. Previously, callers
        had to handle None (which most didn't), leading to AttributeError.
        """
        candidates = []
        
        if agent_type:
            candidates = [a for a in self.get_agents_by_type(agent_type) if a.enabled and capability in a.capabilities]
        else:
            candidates = [a for a in self.get_enabled_agents() if capability in a.capabilities]
        
        if not candidates:
            if fallback:
                # Fallback to SAGE primary agent
                sage = self._agents.get("sage_primary")
                if sage and sage.enabled:
                    logger.warning(
                        f"[AGENT_ROUTER] No agent for capability {capability.value}, "
                        f"falling back to SAGE"
                    )
                    return sage
                # Fallback to any enabled agent
                enabled = self.get_enabled_agents()
                if enabled:
                    logger.warning(
                        f"[AGENT_ROUTER] No agent for capability {capability.value}, "
                        f"falling back to {enabled[0].name}"
                    )
                    return enabled[0]
            logger.warning(f"[AGENT_ROUTER] No available agent for capability: {capability.value}")
            return None
        
        # FIX A-2: Sort by load (ascending) to distribute work evenly
        # across multiple capable agents. Without this, the same agent
        # gets overloaded while others sit idle.
        candidates.sort(key=lambda a: self._agent_load.get(a.agent_id, 0))
        
        # Prefer SAGE for coordination tasks
        sage_agents = [a for a in candidates if a.agent_type == AgentType.SAGE]
        if sage_agents and capability in [AgentCapability.ARCHITECTURE, AgentCapability.CODE_REVIEW]:
            selected = sage_agents[0]
        else:
            selected = candidates[0]
        
        # FIX A-2: Increment load counter for selected agent
        self._agent_load[selected.agent_id] = self._agent_load.get(selected.agent_id, 0) + 1
        
        return selected

    def release_agent(self, agent_id: str) -> None:
        """
        Decrement load counter when a task completes.
        
        FIX A-2: Call this when a task assigned to an agent completes
        to enable accurate load-aware routing.
        """
        if agent_id in self._agent_load and self._agent_load[agent_id] > 0:
            self._agent_load[agent_id] -= 1

    def list_all_agents(self) -> List[Agent]:
        """List all registered agents."""
        return list(self._agents.values())

    def enable_agent(self, agent_id: str) -> bool:
        """Enable an agent."""
        if agent_id in self._agents:
            self._agents[agent_id].enabled = True
            logger.info(f"[AGENT_ROUTER] Enabled agent: {agent_id}")
            return True
        return False

    def disable_agent(self, agent_id: str) -> bool:
        """Disable an agent."""
        if agent_id in self._agents:
            self._agents[agent_id].enabled = False
            logger.info(f"[AGENT_ROUTER] Disabled agent: {agent_id}")
            return True
        return False

    def get_agent_load(self, agent_id: str) -> int:
        """Get current load for an agent. Returns 0 if agent not found."""
        return self._agent_load.get(agent_id, 0)

    def get_all_loads(self) -> Dict[str, int]:
        """Get load map for all agents."""
        return dict(self._agent_load)
