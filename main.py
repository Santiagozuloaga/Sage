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

# The web dashboard is optional. Before this change, main.py hard-imported
# WebServer at the top level, so a missing fastapi/uvicorn/websockets
# install (e.g. before `pip install -r requirements.txt` has fully
# succeeded) prevented SAGE from starting at all - CLI included. That is
# the exact same failure mode just fixed inside kernel._boot_phase() for
# repository_scanner, one layer higher: the entrypoint itself must not let
# an optional interface take down the whole runtime.
try:
    from web.server import WebServer
    WEB_AVAILABLE = True
except ImportError as e:
    WebServer = None
    WEB_AVAILABLE = False
    _web_import_error = e


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
    
    # Initialize additional components
    dashboard = DashboardMonitor()
    await dashboard.initialize()
    
    recovery = RecoverySystem(config_dir)
    await recovery.initialize()
    
    command_mode = CommandMode()
    await command_mode.initialize()
    
    # Register components with kernel
    kernel._components['dashboard'] = dashboard
    kernel._components['recovery'] = recovery
    kernel._components['command_mode'] = command_mode
    
    logger.info("All components initialized")
    
    # Initialize web server (optional - see WEB_AVAILABLE at import time)
    web_server = None
    web_task = None
    if WEB_AVAILABLE:
        web_server = WebServer(kernel, host="127.0.0.1", port=8000)
        web_task = asyncio.create_task(web_server.start())
        logger.info("Web server starting at http://127.0.0.1:8000")
    else:
        logger.warning(
            f"Web dashboard unavailable ({_web_import_error}); "
            "run `pip install -r requirements.txt` to enable it. "
            "Continuing in CLI-only mode."
        )
    
    # CLI interface (optional - web interface is primary)
    cli = CLIInterface(kernel)
    
    print("\n" + "="*70)
    print("SAGE OS v4.5 Runtime Ready")
    print("="*70)
    if WEB_AVAILABLE:
        print("Web Interface: http://127.0.0.1:8000")
    else:
        print("Web Interface: unavailable (missing dependencies - see log)")
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
        if web_server is not None:
            await web_server.stop()
            web_task.cancel()
            try:
                await web_task
            except asyncio.CancelledError:
                pass
        await dashboard.shutdown()
        await recovery.shutdown()
        await command_mode.shutdown()
        await kernel.shutdown()
        logger.info("SAGE OS shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
        sys.exit(0)
