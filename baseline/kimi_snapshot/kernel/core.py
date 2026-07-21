"""
SAGE OS v4.5 Kernel Core

Central orchestrator that manages all system components and lifecycle.
"""

import asyncio
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from .state import KernelState, KernelContext


logger = logging.getLogger(__name__)


class SageKernel:
    """
    The SAGE OS Kernel - central system orchestrator.
    
    Responsibilities:
    - System initialization and boot sequence
    - Component lifecycle management
    - State machine coordination
    - Event routing
    - Error recovery
    """

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".sage_os"
        self.session_id = str(uuid.uuid4())[:8]
        self.context: Optional[KernelContext] = None
        self._components: Dict[str, Any] = {}
        self._degraded: Dict[str, str] = {}  # component_name -> error message
        self._running = False
        self._shutdown_event = asyncio.Event()

    async def boot(self) -> KernelContext:
        """
        Execute the boot sequence.
        
        Flow: BOOT -> KERNEL_READY -> COMMAND_MODE -> WAITING_FOR_USER_COMMAND
        """
        logger.info(f"[KERNEL] Booting SAGE OS v4.5 - Session: {self.session_id}")
        
        # Initialize context
        self.context = KernelContext(
            current_state=KernelState.BOOT,
            session_id=self.session_id,
            boot_time=datetime.now()
        )
        
        # BOOT phase
        await self._boot_phase()
        
        # Transition to KERNEL_READY
        self.context.transition_to(KernelState.KERNEL_READY, "Boot completed")
        logger.info("[KERNEL] System ready")
        
        # Transition to COMMAND_MODE
        self.context.transition_to(KernelState.COMMAND_MODE, "Entering command mode")
        logger.info("[KERNEL] Command mode active")
        
        # Transition to WAITING_FOR_USER_COMMAND
        self.context.transition_to(
            KernelState.WAITING_FOR_USER_COMMAND,
            "Ready for user input"
        )
        
        self._running = True
        return self.context

    async def _boot_phase(self):
        """Execute boot sequence components.

        Components are split into two tiers:

        - Critical (config, memory, event_bus): nothing else can function
          without these, so a failure here aborts boot. This matches what
          "kernel" means — these three are the actual minimal core.
        - Optional (everything else): a failure here is logged and recorded
          in self._degraded, but boot continues. A bug in a peripheral
          module (e.g. repository_scanner) must never prevent the kernel
          from reaching WAITING_FOR_USER_COMMAND. Before this change it did:
          a missing `Optional` import in repository_scanner/dependency_graph.py
          crashed the entire boot sequence with no possibility of recovery.
        """
        logger.info("[BOOT] Initializing components...")

        # --- Critical tier: boot aborts if any of these fail ---
        await self._init_config()
        await self._init_memory()
        await self._init_event_bus()

        # --- Optional tier: failures degrade, never abort ---
        await self._init_optional("agent_router", self._init_agent_router)
        await self._init_optional("dispatcher", self._init_task_dispatcher)
        await self._init_optional("auditor", self._init_auditor)
        await self._init_optional("provider_router", self._init_provider_router)
        await self._init_optional("file_processor", self._init_file_processor)
        await self._init_optional("repository_scanner", self._init_repository_scanner)
        await self._init_optional("image_analyzer", self._init_image_analyzer)

        # --- Wiring: connect already-initialized components together ---
        # dispatcher is initialized before provider_router above (order
        # unchanged from before this fix), so the connection has to happen
        # here, after both exist, rather than at either one's construction
        # time. This is the only wiring added: dispatcher -> provider_router.
        # dispatcher -> agent_router is deliberately NOT wired here - see
        # TaskDispatcher.set_provider_router's docstring for why that one
        # is a reported decision point, not implemented.
        dispatcher = self._components.get("dispatcher")
        provider_router = self._components.get("provider_router")
        if dispatcher is not None and provider_router is not None:
            dispatcher.set_provider_router(provider_router)
            logger.info("[BOOT] Wired dispatcher -> provider_router")

        if self._degraded:
            logger.warning(
                f"[BOOT] Completed in DEGRADED mode — unavailable components: "
                f"{', '.join(sorted(self._degraded.keys()))}. "
                f"Run kernel.degraded_components for details."
            )
        logger.info("[BOOT] All components initialized")

    async def _init_optional(self, name: str, init_fn) -> None:
        """
        Run a non-critical component initializer without letting its
        failure abort the whole boot sequence.

        Why this exists: _boot_phase previously called every _init_* method
        back to back with no exception handling, so any single component
        failure (including in modules unrelated to core kernel function,
        like repository_scanner) took down the entire system. Splitting
        "must exist for the kernel to mean anything" (config/memory/event_bus)
        from "nice to have, degrade if broken" (everything else) is a low-
        coupling fix: a broken peripheral module no longer has the power to
        stop SAGE from booting.
        """
        try:
            await init_fn()
        except Exception as e:
            logger.error(f"[BOOT] Optional component '{name}' failed to initialize: {e}")
            self._degraded[name] = str(e)

    async def _init_config(self):
        """Initialize configuration system."""
        from config.manager import ConfigManager
        config_mgr = ConfigManager(self.config_dir)
        await config_mgr.load()
        self._components['config'] = config_mgr
        logger.debug("[BOOT] Configuration loaded")

    async def _init_memory(self):
        """Initialize engineering memory system."""
        from memory.engine import MemoryEngine
        memory = MemoryEngine(self.config_dir / "memory.db")
        await memory.initialize()
        self._components['memory'] = memory
        logger.debug("[BOOT] Memory system initialized")

    async def _init_event_bus(self):
        """Initialize event bus for system-wide communication."""
        from events.bus import EventBus
        event_bus = EventBus()
        await event_bus.start()
        self._components['event_bus'] = event_bus
        logger.debug("[BOOT] Event bus started")

    async def _init_agent_router(self):
        """Initialize agent router for multi-agent orchestration."""
        from agents.router import AgentRouter
        router = AgentRouter()
        await router.initialize()
        self._components['agent_router'] = router
        logger.debug("[BOOT] Agent router initialized")

    async def _init_task_dispatcher(self):
        """Initialize task dispatcher."""
        from dispatcher.engine import TaskDispatcher
        dispatcher = TaskDispatcher()
        await dispatcher.start()
        self._components['dispatcher'] = dispatcher
        logger.debug("[BOOT] Task dispatcher started")

    async def _init_auditor(self):
        """Initialize integrity auditor."""
        from auditor.engine import IntegrityAuditor
        auditor = IntegrityAuditor()
        await auditor.initialize()
        self._components['auditor'] = auditor
        logger.debug("[BOOT] Integrity auditor initialized")

    async def _init_provider_router(self):
        """Initialize provider router for LLM integration."""
        from providers.provider_router import ProviderRouter
        # Default is "ollama", not "grok": this project's actual target
        # hardware (consumer laptop, no GPU) has no guaranteed cloud budget,
        # and Ollama is the only provider that requires no API key at all.
        # Grok/Gemini remain available and get used automatically whenever
        # their API keys ARE configured (see ProviderRouter.initialize).
        provider_router = ProviderRouter(default_provider="ollama")
        await provider_router.initialize()
        self._components['provider_router'] = provider_router
        logger.debug("[BOOT] Provider router initialized")

    async def _init_file_processor(self):
        """Initialize file processor for file uploads."""
        from file_processor.processor import FileProcessor
        storage_dir = self.config_dir / "uploads"
        file_processor = FileProcessor(storage_dir)
        self._components['file_processor'] = file_processor
        logger.debug("[BOOT] File processor initialized")

    async def _init_repository_scanner(self):
        """Initialize repository scanner."""
        from repository_scanner.scanner import RepositoryScanner
        repo_scanner = RepositoryScanner()
        self._components['repository_scanner'] = repo_scanner
        logger.debug("[BOOT] Repository scanner initialized")

    async def _init_image_analyzer(self):
        """Initialize image analyzer."""
        from image_analysis.analyzer import ImageAnalyzer
        provider_router = self._components.get('provider_router')
        image_analyzer = ImageAnalyzer(provider_router=provider_router)
        self._components['image_analyzer'] = image_analyzer
        logger.debug("[BOOT] Image analyzer initialized")

    async def execute_command(self, command: str) -> Any:
        """
        Execute a user command.
        
        Flow: WAITING_FOR_USER_COMMAND -> COMMAND_EXECUTION -> WAITING_FOR_USER_COMMAND
        """
        if not self._running:
            raise RuntimeError("Kernel not running")
        
        if self.context.current_state != KernelState.WAITING_FOR_USER_COMMAND:
            raise RuntimeError(f"Invalid state for command: {self.context.current_state}")
        
        # Transition to COMMAND_EXECUTION
        self.context.transition_to(KernelState.COMMAND_EXECUTION, f"Executing: {command}")
        self.context.command_count += 1
        logger.info(f"[KERNEL] Executing command #{self.context.command_count}: {command}")
        
        try:
            # Route command through dispatcher
            dispatcher = self._components.get('dispatcher')
            if dispatcher is None:
                raise RuntimeError(
                    "Task dispatcher unavailable — it failed to initialize during "
                    f"boot ({self._degraded.get('dispatcher', 'unknown error')}). "
                    "See kernel.degraded_components for the full list."
                )
            result = await dispatcher.dispatch(command)
            
            # Return to WAITING_FOR_USER_COMMAND (never terminate after READY)
            self.context.transition_to(
                KernelState.WAITING_FOR_USER_COMMAND,
                "Command completed, ready for next"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[KERNEL] Command execution failed: {e}")
            # FIX S-2: Use record_error() instead of just incrementing error_count.
            # This populates last_error for post-mortem debugging.
            # Ported from Runtime Engineer's S-2 fix.
            self.context.record_error(f"Command {command!r} failed: {e}")
            self.context.transition_to(
                KernelState.WAITING_FOR_USER_COMMAND,
                f"Command failed with error: {e}"
            )
            raise

    async def shutdown(self):
        """Graceful shutdown sequence."""
        logger.info("[KERNEL] Initiating shutdown...")
        self._running = False
        
        # Transition to SHUTDOWN
        if self.context:
            self.context.transition_to(KernelState.SHUTDOWN, "System shutdown")
        
        # Shutdown components in reverse order
        for name in reversed(list(self._components.keys())):
            component = self._components[name]
            if hasattr(component, 'shutdown'):
                await component.shutdown()
            logger.debug(f"[KERNEL] Shut down {name}")
        
        self._shutdown_event.set()
        logger.info("[KERNEL] Shutdown complete")

    def get_component(self, name: str) -> Any:
        """Get a registered component by name."""
        return self._components.get(name)

    @property
    def degraded_components(self) -> Dict[str, str]:
        """Optional components that failed to initialize during boot, mapped to their error."""
        return dict(self._degraded)

    @property
    def is_degraded(self) -> bool:
        """Whether the kernel is running with one or more optional components unavailable."""
        return bool(self._degraded)

    @property
    def state(self) -> KernelState:
        """Current kernel state."""
        return self.context.current_state if self.context else KernelState.BOOT

    @property
    def is_running(self) -> bool:
        """Whether the kernel is running."""
        return self._running
