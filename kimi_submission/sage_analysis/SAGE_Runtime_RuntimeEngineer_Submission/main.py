#!/usr/bin/env python3
"""
SAGE OS v4.5 - Local Runtime Entry Point

Main entry point for the SAGE OS local executable runtime.
This is a migration of the SAGE architecture from Opal to a local Python runtime.

Architecture Status: FROZEN
Engineering Status: ACTIVE

This is NOT a redesign. This is NOT a rewrite. This is an extraction and migration.
"""

import asyncio
import logging
import sys
from pathlib import Path

# UTF-8 encoding setup for Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")

# Add sage_runtime to path
sys.path.insert(0, str(Path(__file__).parent))

from kernel import SageKernel
from interface.cli import CLIInterface
from boot.configurator import BootConfigurator
from dashboard.monitor import DashboardMonitor
from recovery.system import RecoverySystem
from command_mode.executor import CommandMode
from web.server import WebServer


def setup_logging():
    """Configure logging for the runtime."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


async def main():
    """Main entry point for SAGE OS runtime."""
    setup_logging()
    logger = logging.getLogger("SAGE_OS")
    
    print("\n" + "="*70)
    print("SAGE OS v4.5 - Local Runtime")
    print("Architecture Status: FROZEN")
    print("Engineering Status: ACTIVE")
    print("="*70 + "\n")
    
    # Configuration directory
    config_dir = Path.home() / ".sage_os"
    
    # Initialize components
    logger.info("Initializing SAGE OS components...")
    
    # Boot configurator
    boot_config = BootConfigurator(config_dir)
    await boot_config.load()
    await boot_config.validate()
    
    # Initialize kernel
    kernel = SageKernel(config_dir)
    await kernel.boot()

    # FIX MAIN-1: previously, main.py constructed a SECOND DashboardMonitor
    # after kernel.boot() had already constructed and registered one (via
    # SageKernel._init_dashboard). The second instance overwrote the first
    # in kernel._components['dashboard'], leaking the first one (its
    # background tasks and resources were never shut down). Now we reuse
    # the dashboard that the kernel already registered, and only construct
    # the components the kernel does NOT own (recovery, command_mode).
    dashboard = kernel.get_component('dashboard')
    if dashboard is None:
        # Defensive fallback — should not happen, but keeps main.py runnable
        # if the kernel's boot phase is ever modified to skip dashboard init.
        dashboard = DashboardMonitor()
        await dashboard.initialize()
        kernel._components['dashboard'] = dashboard

    recovery = RecoverySystem(config_dir)
    await recovery.initialize()
    kernel._components['recovery'] = recovery

    command_mode = CommandMode()
    await command_mode.initialize()
    kernel._components['command_mode'] = command_mode

    logger.info("All components initialized")
    
    # Initialize web server
    web_server = WebServer(kernel, host="127.0.0.1", port=8000)
    
    # Start web server in background
    web_task = asyncio.create_task(web_server.start())
    logger.info("Web server starting at http://127.0.0.1:8000")
    
    # CLI interface (optional - web interface is primary)
    cli = CLIInterface(kernel)
    
    print("\n" + "="*70)
    print("SAGE OS v4.5 Runtime Ready")
    print("="*70)
    print("Web Interface: http://127.0.0.1:8000")
    print("CLI Interface: Available (press Ctrl+C to exit)")
    print("="*70 + "\n")
    
    try:
        # Keep runtime alive
        while kernel.is_running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Runtime error: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("Shutting down components...")
        await web_server.stop()
        web_task.cancel()
        try:
            await web_task
        except asyncio.CancelledError:
            pass
        # FIX MAIN-1 (companion): since dashboard is now owned by the kernel,
        # we no longer shut it down manually — kernel.shutdown() walks the
        # component registry in reverse and calls shutdown() on each one,
        # including dashboard, recovery, and command_mode. Calling
        # dashboard.shutdown() here would double-shut it down.
        await kernel.shutdown()
        logger.info("SAGE OS shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
        sys.exit(0)
