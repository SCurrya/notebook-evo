import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from esperanto import EmbeddingModel

from open_notebook.ai.provider_diagnostics import (
    ProviderAttempt,
    log_provider_failure,
    log_provider_success,
)


def _embedding_endpoint(provider: str, config: Dict[str, Any]) -> str:
    if config.get("endpoint_embedding"):
        return str(config["endpoint_embedding"]).rstrip("/")
    if config.get("base_url"):
        return f"{str(config['base_url']).rstrip('/')}/embeddings"
    if provider == "sensenova":
        return "https://api.sensenova.cn/v1/llm/embeddings"
    if provider == "openrouter":
        return "https://openrouter.ai/api/v1/embeddings"
    raise ValueError(f"No embedding endpoint configured for provider '{provider}'")


@dataclass
class HttpEmbeddingModel(EmbeddingModel):
    provider_name: str = "openai_compatible"

    @property
    def provider(self) -> str:
        return self.provider_name

    def _get_models(self):
        return []

    def _get_default_model(self) -> str:
        return self.model_name or ""

    def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            raise RuntimeError("Synchronous embedding cannot run inside an active event loop")
        return asyncio.run(self.aembed(texts, **kwargs))

    async def aembed(self, texts: List[str], **kwargs) -> List[List[float]]:
        if not texts:
            return []

        model = self.get_model_name()
        if not model:
            raise ValueError(f"No embedding model configured for provider '{self.provider}'")

        config = dict(self.config or {})
        if hasattr(self, "_config"):
            config.update(getattr(self, "_config", {}) or {})
        config.update(kwargs)

        api_key: Optional[str] = config.get("api_key") or self.api_key
        endpoint = _embedding_endpoint(self.provider_name, config)

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if self.provider_name == "openrouter":
            headers.setdefault("HTTP-Referer", "https://open-notebook.local")
            headers.setdefault("X-Title", "Open Notebook")

        payload: Dict[str, Any] = {
            "model": model,
            "input": texts,
        }
        if config.get("encoding_format"):
            payload["encoding_format"] = config["encoding_format"]
        if config.get("dimensions"):
            payload["dimensions"] = config["dimensions"]

        attempt = ProviderAttempt.start(self.provider_name, model, endpoint, 0)
        try:
            async with httpx.AsyncClient(timeout=float(config.get("timeout", 60.0))) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
            data = response.json()
            embeddings = self._extract_embeddings(data)
            if len(embeddings) != len(texts):
                raise ValueError(
                    f"Embedding response count mismatch: got {len(embeddings)} for {len(texts)} input texts"
                )
            log_provider_success(attempt, response.status_code)
            return embeddings
        except Exception as error:
            log_provider_failure(attempt, error)
            raise

    @staticmethod
    def _extract_embeddings(data: Any) -> List[List[float]]:
        if not isinstance(data, dict):
            raise ValueError("Embedding response was not a JSON object")

        items = data.get("data") or data.get("embeddings") or data.get("result")
        if not isinstance(items, list):
            raise ValueError(f"Embedding response missing data array: {list(data.keys())}")

        embeddings: List[List[float]] = []
        for item in items:
            if isinstance(item, dict):
                vector = item.get("embedding") or item.get("vector")
            else:
                vector = item
            if not isinstance(vector, list) or not vector:
                raise ValueError("Embedding item did not contain a vector")
            embeddings.append([float(v) for v in vector])

        return embeddings
