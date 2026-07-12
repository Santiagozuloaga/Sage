"""
SAGE OS Grok Provider

xAI Grok API integration for SAGE Runtime.
"""

import os
import time
import logging
import base64
from typing import List, Dict, Any, Optional

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .base_provider import BaseProvider, ProviderConfig, ProviderResponse, ProviderStatus


logger = logging.getLogger(__name__)


class GrokProvider(BaseProvider):
    """
    xAI Grok API provider.
    
    Environment variable: GROK_API_KEY
    API Base URL: https://api.x.ai/v1
    """

    DEFAULT_MODELS = [
        "grok-beta",
        "grok-2"
    ]

    API_BASE_URL = "https://api.x.ai/v1"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None

    @property
    def provider_name(self) -> str:
        return "grok"

    def _initialize_client(self):
        """Initialize the Grok client."""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed")
        
        if not self._client:
            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.API_BASE_URL,
                timeout=self.config.timeout
            )
            logger.info(f"[GROK] Initialized with model: {self.config.model}")

    async def generate_text(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate text from a prompt."""
        start_time = time.time()
        
        try:
            self._initialize_client()
            
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                **self.config.additional_params
            )
            
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ONLINE)
            self._reset_errors()
            
            return ProviderResponse(
                content=response.choices[0].message.content,
                provider=self.provider_name,
                model=self.config.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                latency_ms=latency_ms,
                finish_reason=response.choices[0].finish_reason,
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None
                }
            )
            
        except Exception as e:
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ERROR)
            self._increment_error()
            logger.error(f"[GROK] Generate text error: {e}")
            raise

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> ProviderResponse:
        """Chat with message history."""
        start_time = time.time()
        
        try:
            self._initialize_client()
            
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                **self.config.additional_params
            )
            
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ONLINE)
            self._reset_errors()
            
            return ProviderResponse(
                content=response.choices[0].message.content,
                provider=self.provider_name,
                model=self.config.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                latency_ms=latency_ms,
                finish_reason=response.choices[0].finish_reason,
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None
                }
            )
            
        except Exception as e:
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ERROR)
            self._increment_error()
            logger.error(f"[GROK] Chat error: {e}")
            raise

    async def analyze_image(self, image_data: bytes, prompt: str, **kwargs) -> ProviderResponse:
        """Analyze an image."""
        start_time = time.time()
        
        try:
            self._initialize_client()
            
            # Encode image to base64
            base64_image = base64.b64encode(image_data).decode()
            
            # Create message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
            
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                **self.config.additional_params
            )
            
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ONLINE)
            self._reset_errors()
            
            return ProviderResponse(
                content=response.choices[0].message.content,
                provider=self.provider_name,
                model=self.config.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                latency_ms=latency_ms,
                finish_reason=response.choices[0].finish_reason,
                metadata={}
            )
            
        except Exception as e:
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ERROR)
            self._increment_error()
            logger.error(f"[GROK] Image analysis error: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check provider health."""
        start_time = time.time()
        
        try:
            self._initialize_client()
            
            # Simple test prompt
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "Health check"}],
                max_tokens=10
            )
            
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ONLINE)
            
            return {
                "status": "online",
                "latency_ms": latency_ms,
                "model": self.config.model,
                "error_count": self._error_count
            }
            
        except Exception as e:
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ERROR)
            self._increment_error()
            
            return {
                "status": "error",
                "latency_ms": latency_ms,
                "error": str(e),
                "error_count": self._error_count
            }

    async def list_models(self) -> List[str]:
        """List available models."""
        if not OPENAI_AVAILABLE:
            return self.DEFAULT_MODELS
        
        try:
            self._initialize_client()
            models = await self._client.models.list()
            model_names = [m.id for m in models.data]
            # Filter for Grok models
            grok_models = [m for m in model_names if "grok" in m.lower()]
            return grok_models if grok_models else self.DEFAULT_MODELS
        except Exception as e:
            logger.error(f"[GROK] List models error: {e}")
            return self.DEFAULT_MODELS

    @classmethod
    def from_env(cls, model: str = "grok-beta") -> 'GrokProvider':
        """Create provider from environment variables."""
        api_key = os.environ.get("GROK_API_KEY")
        if not api_key:
            raise ValueError("GROK_API_KEY environment variable not set")
        
        config = ProviderConfig(
            api_key=api_key,
            model=model
        )
        return cls(config)
