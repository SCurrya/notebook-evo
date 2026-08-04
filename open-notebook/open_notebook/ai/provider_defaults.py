import os
from typing import Dict, Optional

import httpx
from loguru import logger
from pydantic import SecretStr

from open_notebook.ai.models import DefaultModels, Model
from open_notebook.database.repository import repo_query
from open_notebook.domain.credential import Credential

SENSENOVA_PROVIDER = "sensenova"
OPENROUTER_PROVIDER = "openrouter"

SENSENOVA_CHAT_MODEL = "deepseek-v4-flash"
SENSENOVA_TRANSFORM_MODEL = "sensenova-6.7-flash-lite"
SENSENOVA_EMBEDDING_MODEL = "sensenova-embedding"
OPENROUTER_CHAT_FALLBACK_MODEL = "deepseek/deepseek-v4-flash"
OPENROUTER_EMBEDDING_FALLBACK_MODEL = "qwen/qwen3-embedding-4b"

SENSENOVA_CHAT_BASE_URL = "https://api.sensenova.cn/compatible-mode/v2"
SENSENOVA_EMBEDDING_URL = "https://api.sensenova.cn/v1/llm/embeddings"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _env(name: str) -> Optional[str]:
    value = os.getenv(name, "").strip()
    return value or None


async def _get_first_credential(provider: str) -> Optional[Credential]:
    credentials = await Credential.get_by_provider(provider)
    return credentials[0] if credentials else None


async def _ensure_credential(
    *,
    provider: str,
    name: str,
    api_key: Optional[str],
    modalities: list[str],
    base_url: Optional[str] = None,
    endpoint_embedding: Optional[str] = None,
) -> Optional[Credential]:
    existing = await _get_first_credential(provider)
    if existing:
        changed = False
        if name and existing.name != name:
            existing.name = name
            changed = True
        if modalities and sorted(existing.modalities or []) != sorted(modalities):
            existing.modalities = modalities
            changed = True
        if base_url and existing.base_url != base_url:
            existing.base_url = base_url
            changed = True
        if endpoint_embedding and existing.endpoint_embedding != endpoint_embedding:
            existing.endpoint_embedding = endpoint_embedding
            changed = True
        if api_key:
            existing.api_key = SecretStr(api_key)
            changed = True
        if changed:
            await existing.save()
        return existing

    if not api_key:
        logger.warning("Skipping {} credential seed because no API key is configured", provider)
        return None

    credential = Credential(
        name=name,
        provider=provider,
        modalities=modalities,
        api_key=SecretStr(api_key),
        base_url=base_url,
        endpoint_embedding=endpoint_embedding,
    )
    await credential.save()
    return credential


async def _ensure_model(
    *,
    name: str,
    provider: str,
    model_type: str,
    credential_id: Optional[str],
) -> Optional[str]:
    rows = await repo_query(
        """
        SELECT * FROM model
        WHERE string::lowercase(provider) = $provider
          AND string::lowercase(name) = $name
          AND string::lowercase(type) = $type
        LIMIT 1
        """,
        {
            "provider": provider.lower(),
            "name": name.lower(),
            "type": model_type.lower(),
        },
    )
    if rows:
        model = Model(**rows[0])
        if credential_id and model.credential != credential_id:
            model.credential = credential_id
            await model.save()
        return model.id

    model = Model(
        name=name,
        provider=provider,
        type=model_type,
        credential=credential_id,
    )
    await model.save()
    return model.id


async def probe_sensenova_embedding(api_key: Optional[str]) -> bool:
    if not api_key:
        return False
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                SENSENOVA_EMBEDDING_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": SENSENOVA_EMBEDDING_MODEL, "input": ["probe"]},
            )
            if response.status_code == 200:
                data = response.json()
                return bool(data.get("data") or data.get("embeddings") or data.get("result"))
            logger.warning(
                "SenseNova embedding probe failed with HTTP {}: {}",
                response.status_code,
                response.text[:300],
            )
            return False
    except Exception as error:
        logger.warning("SenseNova embedding probe failed: {}", type(error).__name__)
        return False


async def ensure_preferred_provider_setup() -> Dict[str, Optional[str]]:
    """
    Seed the preferred SenseNova-first setup.

    The function is idempotent and intentionally uses environment variables for
    secrets so API keys are not committed to source code.
    """
    sensenova_key = _env("SENSENOVA_API_KEY")
    openrouter_key = _env("OPENROUTER_API_KEY")

    sensenova_cred = await _ensure_credential(
        provider=SENSENOVA_PROVIDER,
        name="SenseNova Primary",
        api_key=sensenova_key,
        modalities=["language", "embedding"],
        base_url=SENSENOVA_CHAT_BASE_URL,
        endpoint_embedding=SENSENOVA_EMBEDDING_URL,
    )
    openrouter_cred = await _ensure_credential(
        provider=OPENROUTER_PROVIDER,
        name="OpenRouter Fallback",
        api_key=openrouter_key,
        modalities=["language", "embedding", "speech_to_text", "text_to_speech"],
        base_url=OPENROUTER_BASE_URL,
        endpoint_embedding=f"{OPENROUTER_BASE_URL}/embeddings",
    )

    sensenova_cred_id = sensenova_cred.id if sensenova_cred else None
    openrouter_cred_id = openrouter_cred.id if openrouter_cred else None

    chat_model_id = await _ensure_model(
        name=SENSENOVA_CHAT_MODEL,
        provider=SENSENOVA_PROVIDER,
        model_type="language",
        credential_id=sensenova_cred_id,
    )
    transform_model_id = await _ensure_model(
        name=SENSENOVA_TRANSFORM_MODEL,
        provider=SENSENOVA_PROVIDER,
        model_type="language",
        credential_id=sensenova_cred_id,
    )
    openrouter_chat_id = await _ensure_model(
        name=OPENROUTER_CHAT_FALLBACK_MODEL,
        provider=OPENROUTER_PROVIDER,
        model_type="language",
        credential_id=openrouter_cred_id,
    )
    openrouter_embedding_id = await _ensure_model(
        name=OPENROUTER_EMBEDDING_FALLBACK_MODEL,
        provider=OPENROUTER_PROVIDER,
        model_type="embedding",
        credential_id=openrouter_cred_id,
    )

    sensenova_embedding_id = None
    if await probe_sensenova_embedding(sensenova_key):
        sensenova_embedding_id = await _ensure_model(
            name=SENSENOVA_EMBEDDING_MODEL,
            provider=SENSENOVA_PROVIDER,
            model_type="embedding",
            credential_id=sensenova_cred_id,
        )

    defaults = await DefaultModels.get_instance()
    defaults.default_chat_model = chat_model_id
    defaults.default_tools_model = chat_model_id
    defaults.large_context_model = chat_model_id
    defaults.default_transformation_model = transform_model_id
    defaults.default_embedding_model = sensenova_embedding_id or openrouter_embedding_id
    await defaults.update()

    logger.info(
        "Preferred AI defaults ensured: chat={} transform={} embedding={} fallback_chat={} fallback_embedding={}",
        chat_model_id,
        transform_model_id,
        defaults.default_embedding_model,
        openrouter_chat_id,
        openrouter_embedding_id,
    )
    return {
        "chat": chat_model_id,
        "transform": transform_model_id,
        "embedding": defaults.default_embedding_model,
        "fallback_chat": openrouter_chat_id,
        "fallback_embedding": openrouter_embedding_id,
    }
