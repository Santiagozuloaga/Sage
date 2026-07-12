"""
SAGE OS Base Provider Interface

Abstract interface for all LLM providers.
All providers must implement this interface to ensure compatibility.
"""

import os
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Provider health status."""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    DEGRADED = "degraded"


@dataclass
class ProviderConfig:
    """Configuration for a provider."""
    api_key: str
    model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30
    additional_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderResponse:
    """Standard response format from all providers."""
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    latency_ms: float = 0.0
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    """
    Abstract base class for all LLM providers.
    
    All providers must implement these methods to ensure
    compatibility with the ProviderRouter and Kernel.
    """

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._status = ProviderStatus.OFFLINE
        self._last_latency_ms = 0.0
        self._error_count = 0

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass

    @property
    def status(self) -> ProviderStatus:
        """Get current provider status."""
        return self._status

    @property
    def last_latency_ms(self) -> float:
        """Get last measured latency in milliseconds."""
        return self._last_latency_ms

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        **kwargs
    ) -> ProviderResponse:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional provider-specific parameters
            
        Returns:
            ProviderResponse with generated text
        """
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> ProviderResponse:
        """
        Chat with the provider using message history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional provider-specific parameters
            
        Returns:
            ProviderResponse with chat response
        """
        pass

    @abstractmethod
    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        **kwargs
    ) -> ProviderResponse:
        """
        Analyze an image with the provider.
        
        Args:
            image_data: Raw image bytes
            prompt: Analysis prompt
            **kwargs: Additional provider-specific parameters
            
        Returns:
            ProviderResponse with image analysis
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check provider health and connectivity.
        
        Returns:
            Dict with health status and metrics
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """
        List available models for this provider.
        
        Returns:
            List of model names/IDs
        """
        pass

    def _measure_latency(self, start_time: float) -> float:
        """Calculate latency in milliseconds."""
        latency_ms = (time.time() - start_time) * 1000
        self._last_latency_ms = latency_ms
        return latency_ms

    def _update_status(self, status: ProviderStatus):
        """Update provider status."""
        self._status = status
        logger.debug(f"[{self.provider_name}] Status: {status.value}")

    def _increment_error(self):
        """Increment error count."""
        self._error_count += 1
        logger.warning(f"[{self.provider_name}] Error count: {self._error_count}")

    def _reset_errors(self):
        """Reset error count."""
        self._error_count = 0

    @classmethod
    def from_env(cls, model: str = "default") -> 'BaseProvider':
        """
        Create provider instance from environment variables.
        
        Subclasses must implement this to load their specific API key.
        """
        raise NotImplementedError("Subclasses must implement from_env")
