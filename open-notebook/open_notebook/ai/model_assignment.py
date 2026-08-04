from typing import Any, ClassVar, Dict, List, Optional

from loguru import logger

from open_notebook.ai.models import DefaultModels
from open_notebook.database.repository import repo_query

PROVIDER_PRIORITY = [
    "sensenova",
    "openrouter",
    "openai",
    "anthropic",
    "google",
    "mistral",
    "groq",
    "deepseek",
    "xai",
    "azure",
    "openai_compatible",
    "voyage",
    "elevenlabs",
    "deepgram",
    "ollama",
    "dashscope",
    "minimax",
]

MODEL_PREFERENCES = {
    "sensenova": [
        "deepseek-v4-flash",
        "sensenova-6.7-flash-lite",
        "sensenova-embedding",
    ],
    "openai": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-5-sonnet", "claude-3-opus", "claude-3-sonnet"],
    "google": ["gemini-2.0", "gemini-1.5-pro", "gemini-pro"],
    "mistral": ["mistral-large", "mixtral"],
    "groq": ["llama-3.3", "llama-3.1", "mixtral"],
    "deepseek": ["deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"],
    "openrouter": [
        "deepseek/deepseek-v4-flash",
        "qwen/qwen3-embedding-4b",
        "deepseek",
        "qwen",
        "gemma",
        "llama",
        "gpt-4o",
        "claude",
    ],
    "openai_compatible": [
        "ds-v4-flash",
        "deepseek-v4-flash",
        "deepseek-chat",
        "gpt-4o",
        "qwen",
        "gemini",
    ],
    "voyage": ["voyage-3", "voyage-3-lite", "voyage-code-3"],
    "elevenlabs": ["eleven_multilingual_v2", "eleven_turbo_v2_5", "scribe_v1"],
    "deepgram": ["aura-2", "aura"],
    "dashscope": ["qwen-max", "qwen-plus", "qwen-turbo"],
    "minimax": ["MiniMax-M2.5", "MiniMax-M2.5-highspeed"],
}


def _get_preferred_model(
    models: List[Dict[str, Any]],
    provider_priority: List[str],
    model_preferences: Dict[str, List[str]],
) -> Optional[Dict[str, Any]]:
    """Select the best model from a list based on provider priority and patterns."""
    if not models:
        return None

    by_provider: Dict[str, List[Dict[str, Any]]] = {}
    for model in models:
        provider = str(model.get("provider", ""))
        by_provider.setdefault(provider, []).append(model)

    for provider in provider_priority:
        if provider not in by_provider:
            continue

        provider_models = by_provider[provider]
        if provider in model_preferences:
            for preference in model_preferences[provider]:
                for model in provider_models:
                    if preference.lower() in str(model.get("name", "")).lower():
                        return model

        return provider_models[0]

    return models[0]


async def auto_assign_default_models() -> Dict[str, Any]:
    """Auto-assign empty default model slots and persist the result."""
    defaults = await DefaultModels.get_instance()

    all_models = await repo_query(
        "SELECT * FROM model ORDER BY provider, name",
        {},
    )

    models_by_type: Dict[str, List[Dict[str, Any]]] = {
        "language": [],
        "embedding": [],
        "text_to_speech": [],
        "speech_to_text": [],
    }

    for model in all_models:
        model_type = str(model.get("type", ""))
        if model_type in models_by_type:
            models_by_type[model_type].append(model)

    slot_configs = [
        (
            "default_chat_model",
            "language",
            defaults.default_chat_model,
            ["deepseek-v4-flash", "deepseek/deepseek-v4-flash"],
        ),
        (
            "default_transformation_model",
            "language",
            defaults.default_transformation_model,
            ["sensenova-6.7-flash-lite", "deepseek-v4-flash"],
        ),
        (
            "default_tools_model",
            "language",
            defaults.default_tools_model,
            ["deepseek-v4-flash", "deepseek/deepseek-v4-flash"],
        ),
        (
            "large_context_model",
            "language",
            defaults.large_context_model,
            ["deepseek-v4-flash", "deepseek/deepseek-v4-flash"],
        ),
        (
            "default_embedding_model",
            "embedding",
            defaults.default_embedding_model,
            ["sensenova-embedding", "qwen/qwen3-embedding-4b"],
        ),
        ("default_text_to_speech_model", "text_to_speech", defaults.default_text_to_speech_model, []),
        ("default_speech_to_text_model", "speech_to_text", defaults.default_speech_to_text_model, []),
    ]

    assigned: Dict[str, str] = {}
    skipped: List[str] = []
    missing: List[str] = []

    for slot_name, model_type, current_value, slot_preferences in slot_configs:
        if current_value:
            skipped.append(slot_name)
            continue

        available_models = models_by_type.get(model_type, [])
        if not available_models:
            missing.append(slot_name)
            continue

        slot_model_preferences = dict(MODEL_PREFERENCES)
        if slot_preferences:
            slot_model_preferences["sensenova"] = slot_preferences
            slot_model_preferences["openrouter"] = slot_preferences

        best_model = _get_preferred_model(
            available_models,
            PROVIDER_PRIORITY,
            slot_model_preferences,
        )

        if best_model:
            model_id = str(best_model.get("id", ""))
            if model_id:
                assigned[slot_name] = model_id
                setattr(defaults, slot_name, model_id)

    if assigned:
        await defaults.update()
        logger.info(
            "Auto-assigned default models: {}",
            ", ".join(f"{slot}={model_id}" for slot, model_id in assigned.items()),
        )

    return {
        "assigned": assigned,
        "skipped": skipped,
        "missing": missing,
    }
