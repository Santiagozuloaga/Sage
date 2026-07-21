"""
SAGE OS Provider Router

Routes requests to LLM providers with automatic fallback.
Kernel communicates only with ProviderRouter, never directly with providers.
"""

import logging
import os
from typing import Dict, List, Optional, Any
from enum import Enum

from .base_provider import BaseProvider, ProviderResponse, ProviderStatus
from .gemini_provider import GeminiProvider
from .grok_provider import GrokProvider
from .ollama_provider import OllamaProvider


logger = logging.getLogger(__name__)


class ProviderSelection(Enum):
    """Provider selection strategy."""
    USER = "user"  # User explicitly selected
    DEFAULT = "default"  # Use default provider
    AUTO = "auto"  # Automatic selection based on availability/latency


class ProviderRouter:
    """
    Router for LLM provider selection and fallback.
    
    The Kernel communicates only with this router.
    Provider selection logic:
    1. User selected provider
    2. Default provider
    3. Automatic fallback
    """

    def __init__(self, default_provider: str = "grok"):
        self._providers: Dict[str, BaseProvider] = {}
        self._default_provider = default_provider
        self._initialized = False

    async def initialize(self):
        """Initialize all available providers from environment variables."""
        logger.info("[PROVIDER_ROUTER] Initializing providers...")

        # NOTE on the pattern below: every provider's health_check() catches
        # its own exceptions internally and returns {"status": "error", ...}
        # instead of raising. Wrapping the health_check() call in try/except
        # (as this method originally did for Grok/Gemini) therefore never
        # actually detects a failed check — it only catches an error in
        # from_env() itself. That meant a provider with a bad/expired key,
        # or Ollama with no local server running, was still being registered
        # as "initialized" and would only fail later, confusingly, on first
        # real use. Fixed by checking the returned status explicitly.

        # Ollama: local, free, no API key required. Attempted unconditionally
        # (not gated behind an env var like Grok/Gemini) because no API key
        # concept applies to it — it either finds a local server or it doesn't.
        try:
            ollama = OllamaProvider.from_env()
            health = await ollama.health_check()
            if health.get("status") == "online":
                self._providers["ollama"] = ollama
                logger.info("[PROVIDER_ROUTER] Ollama provider initialized")
            else:
                logger.warning(
                    f"[PROVIDER_ROUTER] Ollama health check failed "
                    f"(is `ollama serve` running?): {health.get('error')}"
                )
        except Exception as e:
            logger.warning(f"[PROVIDER_ROUTER] Ollama initialization failed: {e}")

        # Initialize Grok if API key is available
        if os.environ.get("GROK_API_KEY"):
            try:
                grok = GrokProvider.from_env()
                health = await grok.health_check()
                if health.get("status") == "online":
                    self._providers["grok"] = grok
                    logger.info("[PROVIDER_ROUTER] Grok provider initialized")
                else:
                    logger.warning(f"[PROVIDER_ROUTER] Grok health check failed: {health.get('error')}")
            except Exception as e:
                logger.warning(f"[PROVIDER_ROUTER] Grok initialization failed: {e}")

        # Initialize Gemini if API key is available
        if os.environ.get("GEMINI_API_KEY"):
            try:
                gemini = GeminiProvider.from_env()
                health = await gemini.health_check()
                if health.get("status") == "online":
                    self._providers["gemini"] = gemini
                    logger.info("[PROVIDER_ROUTER] Gemini provider initialized")
                else:
                    logger.warning(f"[PROVIDER_ROUTER] Gemini health check failed: {health.get('error')}")
            except Exception as e:
                logger.warning(f"[PROVIDER_ROUTER] Gemini initialization failed: {e}")
        
        if not self._providers:
            logger.error(
                "[PROVIDER_ROUTER] No providers initialized - check that "
                "`ollama serve` is running locally, or that GROK_API_KEY / "
                "GEMINI_API_KEY are set"
            )
        
        self._initialized = True
        logger.info(f"[PROVIDER_ROUTER] Initialized with {len(self._providers)} providers")

    def get_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """Get a specific provider by name."""
        return self._providers.get(provider_name)

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return list(self._providers.keys())

    def get_default_provider(self) -> Optional[BaseProvider]:
        """Get the default provider."""
        if self._default_provider in self._providers:
            return self._providers[self._default_provider]
        
        # Fallback to first available if default not available
        if self._providers:
            return next(iter(self._providers.values()))
        
        return None

    def select_provider(
        self,
        selection: ProviderSelection = ProviderSelection.DEFAULT,
        preferred_provider: Optional[str] = None
    ) -> Optional[BaseProvider]:
        """
        Select a provider based on selection strategy.
        
        Args:
            selection: Selection strategy (USER, DEFAULT, AUTO)
            preferred_provider: User's preferred provider (for USER selection)
            
        Returns:
            Selected provider or None if no providers available
        """
        if not self._providers:
            logger.error("[PROVIDER_ROUTER] No providers available")
            return None
        
        if selection == ProviderSelection.USER:
            if preferred_provider and preferred_provider in self._providers:
                logger.info(f"[PROVIDER_ROUTER] Using user-selected provider: {preferred_provider}")
                return self._providers[preferred_provider]
            logger.warning(f"[PROVIDER_ROUTER] User provider '{preferred_provider}' not available, using default")
            return self.get_default_provider()
        
        if selection == ProviderSelection.DEFAULT:
            provider = self.get_default_provider()
            logger.info(f"[PROVIDER_ROUTER] Using default provider: {provider.provider_name if provider else 'None'}")
            return provider
        
        if selection == ProviderSelection.AUTO:
            # Select based on availability and latency
            available_providers = [
                (name, p) for name, p in self._providers.items()
                if p.status == ProviderStatus.ONLINE
            ]
            
            if not available_providers:
                logger.warning("[PROVIDER_ROUTER] No online providers for auto selection")
                return self.get_default_provider()
            
            # Sort by latency (lowest first)
            available_providers.sort(key=lambda x: x[1].last_latency_ms)
            selected_name, selected_provider = available_providers[0]
            logger.info(f"[PROVIDER_ROUTER] Auto-selected provider: {selected_name} (latency: {selected_provider.last_latency_ms:.0f}ms)")
            return selected_provider
        
        return self.get_default_provider()

    async def generate_text(
        self,
        prompt: str,
        provider: str = "auto",
        **kwargs
    ) -> ProviderResponse:
        """
        Generate text with automatic fallback.
        
        Args:
            prompt: Input prompt
            provider: Provider name or "auto"
            **kwargs: Additional parameters
            
        Returns:
            ProviderResponse with generated text
        """
        selection = ProviderSelection.USER if provider != "auto" else ProviderSelection.AUTO
        preferred = provider if provider != "auto" else None
        
        selected_provider = self.select_provider(selection, preferred)
        
        if not selected_provider:
            raise RuntimeError("No providers available")
        
        try:
            logger.info(f"[PROVIDER_ROUTER] Generating text with {selected_provider.provider_name}")
            response = await selected_provider.generate_text(prompt, **kwargs)
            logger.info(f"[PROVIDER_ROUTER] Text generation successful - latency: {response.latency_ms:.0f}ms")
            return response
        except Exception as e:
            logger.error(f"[PROVIDER_ROUTER] Provider {selected_provider.provider_name} failed: {e}")
            
            # Fallback to next available provider
            fallback_provider = self._get_fallback_provider(selected_provider.provider_name)
            if fallback_provider:
                logger.warning(f"[PROVIDER_ROUTER] Falling back to {fallback_provider.provider_name}")
                try:
                    response = await fallback_provider.generate_text(prompt, **kwargs)
                    logger.info(f"[PROVIDER_ROUTER] Fallback successful - latency: {response.latency_ms:.0f}ms")
                    return response
                except Exception as fallback_error:
                    logger.error(f"[PROVIDER_ROUTER] Fallback also failed: {fallback_error}")
            
            raise RuntimeError(f"All providers failed. Last error: {e}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        provider: str = "auto",
        **kwargs
    ) -> ProviderResponse:
        """
        Chat with automatic fallback.
        
        Args:
            messages: Message history
            provider: Provider name or "auto"
            **kwargs: Additional parameters
            
        Returns:
            ProviderResponse with chat response
        """
        selection = ProviderSelection.USER if provider != "auto" else ProviderSelection.AUTO
        preferred = provider if provider != "auto" else None
        
        selected_provider = self.select_provider(selection, preferred)
        
        if not selected_provider:
            raise RuntimeError("No providers available")
        
        try:
            logger.info(f"[PROVIDER_ROUTER] Chat with {selected_provider.provider_name}")
            response = await selected_provider.chat(messages, **kwargs)
            logger.info(f"[PROVIDER_ROUTER] Chat successful - latency: {response.latency_ms:.0f}ms")
            return response
        except Exception as e:
            logger.error(f"[PROVIDER_ROUTER] Provider {selected_provider.provider_name} failed: {e}")
            
            # Fallback to next available provider
            fallback_provider = self._get_fallback_provider(selected_provider.provider_name)
            if fallback_provider:
                logger.warning(f"[PROVIDER_ROUTER] Falling back to {fallback_provider.provider_name}")
                try:
                    response = await fallback_provider.chat(messages, **kwargs)
                    logger.info(f"[PROVIDER_ROUTER] Fallback successful - latency: {response.latency_ms:.0f}ms")
                    return response
                except Exception as fallback_error:
                    logger.error(f"[PROVIDER_ROUTER] Fallback also failed: {fallback_error}")
            
            raise RuntimeError(f"All providers failed. Last error: {e}")

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        provider: str = "auto",
        **kwargs
    ) -> ProviderResponse:
        """
        Analyze image with automatic fallback.
        
        Args:
            image_data: Raw image bytes
            prompt: Analysis prompt
            provider: Provider name or "auto"
            **kwargs: Additional parameters
            
        Returns:
            ProviderResponse with image analysis
        """
        selection = ProviderSelection.USER if provider != "auto" else ProviderSelection.AUTO
        preferred = provider if provider != "auto" else None
        
        selected_provider = self.select_provider(selection, preferred)
        
        if not selected_provider:
            raise RuntimeError("No providers available")
        
        try:
            logger.info(f"[PROVIDER_ROUTER] Image analysis with {selected_provider.provider_name}")
            response = await selected_provider.analyze_image(image_data, prompt, **kwargs)
            logger.info(f"[PROVIDER_ROUTER] Image analysis successful - latency: {response.latency_ms:.0f}ms")
            return response
        except Exception as e:
            logger.error(f"[PROVIDER_ROUTER] Provider {selected_provider.provider_name} failed: {e}")
            
            # Fallback to next available provider
            fallback_provider = self._get_fallback_provider(selected_provider.provider_name)
            if fallback_provider:
                logger.warning(f"[PROVIDER_ROUTER] Falling back to {fallback_provider.provider_name}")
                try:
                    response = await fallback_provider.analyze_image(image_data, prompt, **kwargs)
                    logger.info(f"[PROVIDER_ROUTER] Fallback successful - latency: {response.latency_ms:.0f}ms")
                    return response
                except Exception as fallback_error:
                    logger.error(f"[PROVIDER_ROUTER] Fallback also failed: {fallback_error}")
            
            raise RuntimeError(f"All providers failed. Last error: {e}")

    def _get_fallback_provider(self, failed_provider: str) -> Optional[BaseProvider]:
        """Get next available provider for fallback."""
        available = [
            (name, p) for name, p in self._providers.items()
            if name != failed_provider and p.status == ProviderStatus.ONLINE
        ]
        
        if not available:
            return None
        
        # Sort by latency
        available.sort(key=lambda x: x[1].last_latency_ms)
        return available[0][1]

    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all providers."""
        status = {}
        
        for name, provider in self._providers.items():
            try:
                health = await provider.health_check()
                status[name] = health
            except Exception as e:
                status[name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return status

    async def shutdown(self):
        """Shutdown all providers."""
        logger.info("[PROVIDER_ROUTER] Shutting down providers")
        self._providers.clear()
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if router is initialized."""
        return self._initialized
