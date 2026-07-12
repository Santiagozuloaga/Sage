"""
SAGE OS Provider Configuration

Loads provider configuration from environment variables.
Never stores API keys in source code.
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class ProviderSettings:
    """Settings for a provider."""
    enabled: bool = True
    model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30


class ProviderConfig:
    """
    Provider configuration manager.
    
    Loads configuration from environment variables only.
    Never commits secrets to source code.
    """

    def __init__(self):
        self._settings: Dict[str, ProviderSettings] = {
            "grok": ProviderSettings(
                enabled=bool(os.environ.get("GROK_API_KEY")),
                model=os.environ.get("GROK_MODEL", "grok-beta"),
                temperature=float(os.environ.get("GROK_TEMPERATURE", "0.7")),
                max_tokens=int(os.environ.get("GROK_MAX_TOKENS", "2048")),
                timeout=int(os.environ.get("GROK_TIMEOUT", "30"))
            ),
            "gemini": ProviderSettings(
                enabled=bool(os.environ.get("GEMINI_API_KEY")),
                model=os.environ.get("GEMINI_MODEL", "gemini-1.5-pro"),
                temperature=float(os.environ.get("GEMINI_TEMPERATURE", "0.7")),
                max_tokens=int(os.environ.get("GEMINI_MAX_TOKENS", "2048")),
                timeout=int(os.environ.get("GEMINI_TIMEOUT", "30"))
            )
        }
        self._default_provider = os.environ.get("SAGE_DEFAULT_PROVIDER", "grok")

    def get_settings(self, provider_name: str) -> Optional[ProviderSettings]:
        """Get settings for a specific provider."""
        return self._settings.get(provider_name)

    def is_enabled(self, provider_name: str) -> bool:
        """Check if a provider is enabled."""
        settings = self.get_settings(provider_name)
        return settings.enabled if settings else False

    def get_default_provider(self) -> str:
        """Get the default provider name."""
        return self._default_provider

    def set_default_provider(self, provider_name: str):
        """Set the default provider."""
        if provider_name in self._settings:
            self._default_provider = provider_name
            logger.info(f"[PROVIDER_CONFIG] Default provider set to: {provider_name}")
        else:
            logger.warning(f"[PROVIDER_CONFIG] Unknown provider: {provider_name}")

    def get_all_settings(self) -> Dict[str, ProviderSettings]:
        """Get all provider settings."""
        return self._settings.copy()

    def validate_environment(self) -> Dict[str, bool]:
        """
        Validate that required environment variables are set.
        
        Returns:
            Dict mapping provider names to availability status
        """
        validation = {}
        
        for provider_name in self._settings:
            api_key_env = f"{provider_name.upper()}_API_KEY"
            has_key = bool(os.environ.get(api_key_env))
            validation[provider_name] = has_key
            
            if has_key:
                logger.info(f"[PROVIDER_CONFIG] {provider_name}: API key found")
            else:
                logger.warning(f"[PROVIDER_CONFIG] {provider_name}: API key not found")
        
        return validation

    def get_api_key(self, provider_name: str) -> Optional[str]:
        """
        Get API key for a provider.
        
        WARNING: This returns the actual API key. Use carefully.
        Never log or print this value.
        """
        env_var = f"{provider_name.upper()}_API_KEY"
        return os.environ.get(env_var)
