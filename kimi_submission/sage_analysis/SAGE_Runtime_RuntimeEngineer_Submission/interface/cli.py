"""
SAGE OS CLI Interface

Interactive command-line interface for SAGE OS.
Always remains interactive, never enters read-only mode.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

if sys.platform == "win32":
    import os
    os.system("")  # Enable ANSI escape codes


logger = logging.getLogger(__name__)


class CLIInterface:
    """
    CLI Interface for SAGE OS.
    
    Provides interactive command-line interface that
    always remains interactive and never enters read-only mode.
    """

    def __init__(self, kernel):
        self.kernel = kernel
        self._running = False
        self._prompt = "SAGE > "

    async def start(self):
        """Start the CLI interface."""
        self._running = True
        logger.info("[CLI] Interface started")
        await self._welcome_message()
        await self._command_loop()

    async def _welcome_message(self):
        """Display welcome message."""
        print("\n" + "="*60)
        print("SAGE OS v4.5 - Local Runtime")
        print("="*60)
        print(f"Session ID: {self.kernel.session_id}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Kernel State: {self.kernel.state.value}")
        print("="*60)
        print("\nType 'help' for available commands or enter a command to execute.")
        print("The interface is always interactive - never enters read-only mode.\n")

    async def _command_loop(self):
        """Main command loop."""
        while self._running and self.kernel.is_running:
            try:
                # Get user input
                command = await self._get_input()
                
                if not command:
                    continue
                
                # Handle special commands
                if command.lower() in ('exit', 'quit', 'q'):
                    await self._handle_exit()
                    break
                
                if command.lower() == 'help':
                    await self._show_help()
                    continue
                
                if command.lower() == 'status':
                    await self._show_status()
                    continue
                
                if command.lower() == 'agents':
                    await self._show_agents()
                    continue
                
                if command.lower().startswith('agent '):
                    await self._handle_agent_command(command)
                    continue
                
                # Execute command through kernel
                try:
                    result = await self.kernel.execute_command(command)
                    print(f"\nResult: {result}\n")
                except Exception as e:
                    print(f"\nError: {e}\n")
                    logger.error(f"[CLI] Command error: {e}")
                
            except KeyboardInterrupt:
                print("\n\nInterrupt received. Type 'exit' to quit or continue working.")
                continue
            except EOFError:
                await self._handle_exit()
                break
            except Exception as e:
                logger.error(f"[CLI] Loop error: {e}")
                continue

    async def _get_input(self) -> str:
        """Get input from user."""
        try:
            # Use asyncio to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, input, self._prompt)
        except (EOFError, KeyboardInterrupt):
            raise

    async def _handle_exit(self):
        """Handle exit command."""
        print("\nShutting down SAGE OS...")
        self._running = False
        await self.kernel.shutdown()

    async def _show_help(self):
        """Show help information."""
        print("\n" + "="*60)
        print("Available Commands:")
        print("="*60)
        print("  help          - Show this help message")
        print("  status        - Show system status")
        print("  agents        - List available agents")
        print("  agent <id>    - Switch to specific agent")
        print("  exit/quit/q   - Shutdown SAGE OS")
        print("\n  Any other input will be executed as a command.")
        print("="*60 + "\n")

    async def _show_status(self):
        """Show system status."""
        print("\n" + "="*60)
        print("System Status:")
        print("="*60)
        print(f"  Session ID: {self.kernel.session_id}")
        print(f"  Kernel State: {self.kernel.state.value}")
        print(f"  Command Count: {self.kernel.context.command_count}")
        print(f"  Error Count: {self.kernel.context.error_count}")
        print(f"  Uptime: {(datetime.now() - self.kernel.context.boot_time).total_seconds():.1f}s")
        print("="*60 + "\n")

    async def _show_agents(self):
        """Show available agents."""
        router = self.kernel.get_component('agent_router')
        if not router:
            print("\nAgent router not available.\n")
            return
        
        agents = router.list_all_agents()
        print("\n" + "="*60)
        print("Available Agents:")
        print("="*60)
        for agent in agents:
            status = "ENABLED" if agent.enabled else "DISABLED"
            print(f"  [{status}] {agent.name} ({agent.agent_type.value})")
            print(f"         {agent.description}")
        print("="*60 + "\n")

    async def _handle_agent_command(self, command: str):
        """Handle agent-specific commands."""
        parts = command.split()
        if len(parts) < 2:
            print("Usage: agent <agent_id>")
            return
        
        agent_id = parts[1]
        router = self.kernel.get_component('agent_router')
        if not router:
            print("Agent router not available.")
            return
        
        agent = router.get_agent(agent_id)
        if agent:
            print(f"\nAgent: {agent.name}")
            print(f"Type: {agent.agent_type.value}")
            print(f"Description: {agent.description}")
            print(f"Capabilities: {', '.join([c.value for c in agent.capabilities])}")
            print(f"Status: {'ENABLED' if agent.enabled else 'DISABLED'}\n")
        else:
            print(f"Agent '{agent_id}' not found.\n")

    def stop(self):
        """Stop the CLI interface."""
        self._running = False
