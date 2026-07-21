"""
SAGE OS Ollama Provider

Local Ollama integration for SAGE Runtime, via Ollama's OpenAI-compatible endpoint.

Why this exists: providers/ shipped with only Gemini and Grok, both of which
require a paid cloud API key to register at all (see ProviderRouter.initialize).
Every other part of this project (ClawSpring, OpenClaw Gateway) runs on local
Ollama models because the actual target hardware (consumer laptop, no GPU, no
guaranteed cloud budget) can't depend on a funded cloud key being present.
Without this provider, ProviderRouter starts with zero usable providers on
that machine by default — SAGE OS could boot but could not do any LLM-backed
work at all. This is the one provider that must always be attempted.
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


class OllamaProvider(BaseProvider):
    """
    Local Ollama provider, via Ollama's OpenAI-compatible endpoint
    (http://localhost:11434/v1 by default).

    No API key required — Ollama serves unauthenticated on localhost.

    Environment variables (both optional):
      OLLAMA_BASE_URL  (default: http://localhost:11434/v1)
      OLLAMA_MODEL      (default: qwen2.5:1.5b — the model documented
                          elsewhere in this project as the working balance
                          of speed/capability on the actual target hardware)
    """

    DEFAULT_MODELS = ["qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b"]
    DEFAULT_BASE_URL = "http://localhost:11434/v1"
    DEFAULT_MODEL = "qwen2.5:1.5b"

    def __init__(self, config: ProviderConfig, base_url: str = DEFAULT_BASE_URL):
        super().__init__(config)
        self._client = None
        self._base_url = base_url

    @property
    def provider_name(self) -> str:
        return "ollama"

    def _initialize_client(self):
        """Initialize the Ollama client (OpenAI-compatible local endpoint)."""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed")

        if not self._client:
            self._client = AsyncOpenAI(
                # Ollama does not validate this key, but the OpenAI SDK
                # requires a non-empty string to construct the client.
                api_key=self.config.api_key or "ollama",
                base_url=self._base_url,
                timeout=self.config.timeout
            )
            logger.info(f"[OLLAMA] Initialized with model: {self.config.model} at {self._base_url}")

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
            self._measure_latency(start_time)
            self._update_status(ProviderStatus.ERROR)
            self._increment_error()
            logger.error(f"[OLLAMA] Generate text error: {e}")
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
            self._measure_latency(start_time)
            self._update_status(ProviderStatus.ERROR)
            self._increment_error()
            logger.error(f"[OLLAMA] Chat error: {e}")
            raise

    async def analyze_image(self, image_data: bytes, prompt: str, **kwargs) -> ProviderResponse:
        """
        Analyze an image.

        Note: the small local models documented elsewhere in this project
        (qwen2.5 0.5b/1.5b/3b) are text-only. This will raise whatever error
        the model/server returns rather than pretending to support vision —
        callers needing image analysis on a text-only local model should
        catch this and fall back to a cloud provider explicitly.
        """
        start_time = time.time()
        try:
            self._initialize_client()
            base64_image = base64.b64encode(image_data).decode()
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }]
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
            self._measure_latency(start_time)
            self._update_status(ProviderStatus.ERROR)
            self._increment_error()
            logger.error(f"[OLLAMA] Image analysis error (model '{self.config.model}' may not support vision): {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check provider health by hitting the local Ollama endpoint."""
        start_time = time.time()
        try:
            self._initialize_client()
            await self._client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
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
        """List models actually pulled in the local Ollama installation."""
        if not OPENAI_AVAILABLE:
            return self.DEFAULT_MODELS
        try:
            self._initialize_client()
            models = await self._client.models.list()
            model_names = [m.id for m in models.data]
            return model_names if model_names else self.DEFAULT_MODELS
        except Exception as e:
            logger.error(f"[OLLAMA] List models error: {e}")
            return self.DEFAULT_MODELS

    @classmethod
    def from_env(cls, model: Optional[str] = None) -> 'OllamaProvider':
        """
        Create provider from environment variables.

        Unlike GrokProvider/GeminiProvider.from_env, this never raises for a
        missing API key — Ollama doesn't use one, by design.
        """
        base_url = os.environ.get("OLLAMA_BASE_URL", cls.DEFAULT_BASE_URL)
        selected_model = model or os.environ.get("OLLAMA_MODEL", cls.DEFAULT_MODEL)
        config = ProviderConfig(api_key="ollama", model=selected_model)
        return cls(config, base_url=base_url)
