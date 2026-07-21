"""
SAGE OS v4.5 Kernel Module

The kernel is the central orchestrator of the SAGE runtime.
It manages system initialization, component lifecycle, and core services.
"""

from .core import SageKernel
from .state import KernelState

__all__ = ['SageKernel', 'KernelState']
