"""
SAGE OS Gemini Provider

Google Gemini API integration for SAGE Runtime.
"""

import os
import time
import logging
import base64
from typing import List, Dict, Any, Optional

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from .base_provider import BaseProvider, ProviderConfig, ProviderResponse, ProviderStatus


logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """
    Google Gemini API provider.
    
    Environment variable: GEMINI_API_KEY
    """

    DEFAULT_MODELS = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.0-pro"
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        self._model = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _initialize_client(self):
        """Initialize the Gemini client."""
        if not GENAI_AVAILABLE:
            raise ImportError("google-generativeai package not installed")
        
        if not self._client:
            genai.configure(api_key=self.config.api_key)
            self._client = genai
            self._model = self._client.GenerativeModel(self.config.model)
            logger.info(f"[GEMINI] Initialized with model: {self.config.model}")

    async def generate_text(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate text from a prompt."""
        start_time = time.time()
        
        try:
            self._initialize_client()
            
            # Merge kwargs with config
            generation_config = {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_output_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                **self.config.additional_params
            }
            
            result = await self._model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(**generation_config)
            )
            
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ONLINE)
            self._reset_errors()
            
            return ProviderResponse(
                content=result.text,
                provider=self.provider_name,
                model=self.config.model,
                tokens_used=result.usage_metadata.total_token_count if hasattr(result, 'usage_metadata') else None,
                latency_ms=latency_ms,
                finish_reason=result.candidates[0].finish_reason.name if result.candidates else None,
                metadata={
                    "safety_ratings": [r.category.name for r in result.candidates[0].safety_ratings] if result.candidates else []
                }
            )
            
        except Exception as e:
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ERROR)
            self._increment_error()
            logger.error(f"[GEMINI] Generate text error: {e}")
            raise

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> ProviderResponse:
        """Chat with message history."""
        start_time = time.time()
        
        try:
            self._initialize_client()
            
            # Convert messages to Gemini format
            chat_history = []
            for msg in messages[:-1]:  # All but last message
                role = "user" if msg["role"] == "user" else "model"
                chat_history.append({
                    "role": role,
                    "parts": [msg["content"]]
                })
            
            # Start chat with history
            chat = self._model.start_chat(history=chat_history)
            
            # Send last message
            last_message = messages[-1]["content"]
            response = await chat.send_message_async(
                last_message,
                generation_config=genai.types.GenerationConfig(
                    temperature=kwargs.get("temperature", self.config.temperature),
                    max_output_tokens=kwargs.get("max_tokens", self.config.max_tokens)
                )
            )
            
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ONLINE)
            self._reset_errors()
            
            return ProviderResponse(
                content=response.text,
                provider=self.provider_name,
                model=self.config.model,
                tokens_used=response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None,
                latency_ms=latency_ms,
                finish_reason=response.candidates[0].finish_reason.name if response.candidates else None,
                metadata={}
            )
            
        except Exception as e:
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ERROR)
            self._increment_error()
            logger.error(f"[GEMINI] Chat error: {e}")
            raise

    async def analyze_image(self, image_data: bytes, prompt: str, **kwargs) -> ProviderResponse:
        """Analyze an image."""
        start_time = time.time()
        
        try:
            self._initialize_client()
            
            # Create image part
            image_part = {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_data).decode()
            }
            
            # Generate content with image
            response = await self._model.generate_content_async(
                [prompt, image_part],
                generation_config=genai.types.GenerationConfig(
                    temperature=kwargs.get("temperature", self.config.temperature),
                    max_output_tokens=kwargs.get("max_tokens", self.config.max_tokens)
                )
            )
            
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ONLINE)
            self._reset_errors()
            
            return ProviderResponse(
                content=response.text,
                provider=self.provider_name,
                model=self.config.model,
                tokens_used=response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None,
                latency_ms=latency_ms,
                finish_reason=response.candidates[0].finish_reason.name if response.candidates else None,
                metadata={}
            )
            
        except Exception as e:
            latency_ms = self._measure_latency(start_time)
            self._update_status(ProviderStatus.ERROR)
            self._increment_error()
            logger.error(f"[GEMINI] Image analysis error: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check provider health."""
        start_time = time.time()
        
        try:
            self._initialize_client()
            
            # Simple test prompt
            test_response = await self._model.generate_content_async(
                "Health check",
                generation_config=genai.types.GenerationConfig(max_output_tokens=10)
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
        if not GENAI_AVAILABLE:
            return []
        
        try:
            self._initialize_client()
            models = [m.name for m in genai.list_models()]
            # Filter for generative models
            generative_models = [m for m in models if "generate" in m]
            return generative_models if generative_models else self.DEFAULT_MODELS
        except Exception as e:
            logger.error(f"[GEMINI] List models error: {e}")
            return self.DEFAULT_MODELS

    @classmethod
    def from_env(cls, model: str = "gemini-1.5-pro") -> 'GeminiProvider':
        """Create provider from environment variables."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        config = ProviderConfig(
            api_key=api_key,
            model=model
        )
        return cls(config)
