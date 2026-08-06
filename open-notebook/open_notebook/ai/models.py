import os
from typing import Any, ClassVar, Dict, Optional, Union

from esperanto import (
    AIFactory,
    EmbeddingModel,
    LanguageModel,
    SpeechToTextModel,
    TextToSpeechModel,
)
from loguru import logger

from open_notebook.ai.http_embedding import HttpEmbeddingModel
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel, RecordModel
from open_notebook.exceptions import ConfigurationError

ModelType = Union[LanguageModel, EmbeddingModel, SpeechToTextModel, TextToSpeechModel]


class Model(ObjectModel):
    table_name: ClassVar[str] = "model"
    nullable_fields: ClassVar[set[str]] = {"credential"}
    name: str
    provider: str
    type: str
    credential: Optional[str] = None

    @classmethod
    async def get_models_by_type(cls, model_type):
        models = await repo_query(
            "SELECT * FROM model WHERE type=$model_type;", {"model_type": model_type}
        )
        return [Model(**model) for model in models]

    @classmethod
    async def get_by_credential(cls, credential_id: str):
        """Get all models linked to a specific credential."""
        models = await repo_query(
            "SELECT * FROM model WHERE credential=$cred_id;",
            {"cred_id": ensure_record_id(credential_id)},
        )
        return [Model(**model) for model in models]

    def _prepare_save_data(self) -> Dict[str, Any]:
        data = super()._prepare_save_data()
        if data.get("credential"):
            data["credential"] = ensure_record_id(data["credential"])
        return data

    async def get_credential_obj(self):
        """Get the Credential object linked to this model, if any."""
        if not self.credential:
            return None
        from open_notebook.domain.credential import Credential

        try:
            return await Credential.get(self.credential)
        except Exception:
            logger.warning(f"Could not load credential {self.credential} for model {self.id}")
            return None


class DefaultModels(RecordModel):
    record_id: ClassVar[str] = "open_notebook:default_models"
    default_chat_model: Optional[str] = None
    default_transformation_model: Optional[str] = None
    large_context_model: Optional[str] = None
    default_text_to_speech_model: Optional[str] = None
    default_speech_to_text_model: Optional[str] = None
    # default_vision_model: Optional[str]
    default_embedding_model: Optional[str] = None
    default_tools_model: Optional[str] = None

    @classmethod
    async def get_instance(cls) -> "DefaultModels":
        """Always fetch fresh defaults from database (override parent caching behavior)"""
        result = await repo_query(
            "SELECT * FROM ONLY $record_id",
            {"record_id": ensure_record_id(cls.record_id)},
        )

        if result:
            if isinstance(result, list) and len(result) > 0:
                data = result[0]
            elif isinstance(result, dict):
                data = result
            else:
                data = {}
        else:
            data = {}

        # Create new instance with fresh data (bypass singleton cache)
        instance = object.__new__(cls)
        object.__setattr__(instance, "__dict__", {})
        super(RecordModel, instance).__init__(**data)
        return instance


class ModelManager:
    def __init__(self):
        pass  # No caching needed

    async def get_model_record(self, model_id: str) -> Model:
        if not model_id:
            raise ConfigurationError("Model ID is required")

        try:
            return await Model.get(model_id)
        except Exception:
            raise ConfigurationError(f"Model with ID {model_id} not found")

    async def get_model(self, model_id: str, **kwargs) -> Optional[ModelType]:
        """Get a model by ID. Esperanto will cache the actual model instance."""
        if not model_id:
            return None

        model = await self.get_model_record(model_id)

        if not model.type or model.type not in [
            "language",
            "embedding",
            "speech_to_text",
            "text_to_speech",
        ]:
            raise ConfigurationError(f"Invalid model type: {model.type}")

        # Build config from credential if linked, otherwise fall back to env vars
        config: dict = {}
        if model.credential:
            credential = await model.get_credential_obj()
            if credential:
                config = credential.to_esperanto_config()
                logger.debug(
                    f"Using credential '{credential.name}' for model {model.name}"
                )
            else:
                logger.warning(
                    f"Model {model.id} has credential {model.credential} but it could not be loaded. "
                    f"Falling back to env vars."
                )
                # Fall back to env var provisioning
                from open_notebook.ai.key_provider import provision_provider_keys

                await provision_provider_keys(model.provider)
        else:
            # No credential linked - use env var fallback
            from open_notebook.ai.key_provider import provision_provider_keys

            await provision_provider_keys(model.provider)

        # For openai_compatible without a DB credential, build config from env
        # so Esperanto targets the right base_url instead of api.openai.com.
        if not model.credential and model.provider.lower() == "openai_compatible":
            config.setdefault("api_key", os.getenv("OPENAI_COMPATIBLE_API_KEY"))
            config.setdefault("base_url", os.getenv("OPENAI_COMPATIBLE_BASE_URL"))

        # Merge any additional kwargs (e.g. temperature)
        config.update(kwargs)

        # Normalize provider name: DB stores underscores but Esperanto expects hyphens
        provider_name = model.provider.lower()
        provider = provider_name.replace("_", "-")

        if provider_name == "sensenova":
            if model.type == "language":
                provider = "openai-compatible"
                config.setdefault(
                    "base_url", "https://api.sensenova.cn/compatible-mode/v2"
                )
            elif model.type == "embedding":
                config.setdefault(
                    "endpoint_embedding", "https://api.sensenova.cn/v1/llm/embeddings"
                )
                return HttpEmbeddingModel(
                    model_name=model.name,
                    provider_name="sensenova",
                    api_key=config.get("api_key"),
                    base_url=config.get("base_url"),
                    config=config,
                )

        if provider_name == "openrouter" and model.type == "embedding":
            config.setdefault("base_url", "https://openrouter.ai/api/v1")
            config.setdefault(
                "endpoint_embedding", "https://openrouter.ai/api/v1/embeddings"
            )
            return HttpEmbeddingModel(
                model_name=model.name,
                provider_name="openrouter",
                api_key=config.get("api_key"),
                base_url=config.get("base_url"),
                config=config,
            )

        # Create model based on type (Esperanto will cache the instance)
        if model.type == "language":
            return AIFactory.create_language(
                model_name=model.name,
                provider=provider,
                config=config,
            )
        elif model.type == "embedding":
            return AIFactory.create_embedding(
                model_name=model.name,
                provider=provider,
                config=config,
            )
        elif model.type == "speech_to_text":
            return AIFactory.create_speech_to_text(
                model_name=model.name,
                provider=provider,
                config=config,
            )
        elif model.type == "text_to_speech":
            return AIFactory.create_text_to_speech(
                model_name=model.name,
                provider=provider,
                config=config,
            )
        else:
            raise ConfigurationError(f"Invalid model type: {model.type}")

    async def get_fallback_model_ids(
        self,
        model_type: str,
        primary_model_id: Optional[str] = None,
    ) -> list[str]:
        """Return fallback model IDs ordered by the SenseNova -> OpenRouter policy."""
        if model_type in {"chat", "tools", "large_context", "transformation"}:
            type_filter = "language"
            preferences = [
                "deepseek/deepseek-v4-flash",
            ]
        elif model_type == "embedding":
            type_filter = "embedding"
            preferences = [
                "qwen/qwen3-embedding-4b",
                "nvidia/llama-nemotron-embed-vl-1b-v2:free",
                "perplexity/pplx-embed-v1-0.6b",
                "thenlper/gte-base",
            ]
        else:
            return []

        rows = await repo_query(
            """
            SELECT * FROM model
            WHERE string::lowercase(provider) = 'openrouter'
              AND string::lowercase(type) = $type
            """,
            {"type": type_filter},
        )
        if not rows:
            return []

        candidates = [Model(**row) for row in rows if str(row.get("id")) != primary_model_id]
        ordered: list[Model] = []
        for preference in preferences:
            for model in candidates:
                if model in ordered:
                    continue
                if preference.lower() == model.name.lower():
                    ordered.append(model)
        return [model.id for model in ordered if model.id]

    async def get_defaults(self) -> DefaultModels:
        """Get the default models configuration from database"""
        defaults = await DefaultModels.get_instance()
        if not defaults:
            raise RuntimeError("Failed to load default models configuration")
        return defaults

    async def get_speech_to_text(self, **kwargs) -> Optional[SpeechToTextModel]:
        """Get the default speech-to-text model"""
        defaults = await self.get_defaults()
        model_id = defaults.default_speech_to_text_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, SpeechToTextModel), (
            f"Expected SpeechToTextModel but got {type(model)}"
        )
        return model

    async def get_text_to_speech(self, **kwargs) -> Optional[TextToSpeechModel]:
        """Get the default text-to-speech model"""
        defaults = await self.get_defaults()
        model_id = defaults.default_text_to_speech_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, TextToSpeechModel), (
            f"Expected TextToSpeechModel but got {type(model)}"
        )
        return model

    async def get_embedding_model(self, **kwargs) -> Optional[EmbeddingModel]:
        """Get the default embedding model"""
        defaults = await self.get_defaults()
        model_id = defaults.default_embedding_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, EmbeddingModel), (
            f"Expected EmbeddingModel but got {type(model)}"
        )
        return model

    async def get_default_model(self, model_type: str, **kwargs) -> Optional[ModelType]:
        """
        Get the default model for a specific type.

        Args:
            model_type: The type of model to retrieve (e.g., 'chat', 'embedding', etc.)
            **kwargs: Additional arguments to pass to the model constructor
        """
        defaults = await self.get_defaults()
        model_id = None

        if model_type == "chat":
            model_id = defaults.default_chat_model
        elif model_type == "transformation":
            model_id = (
                defaults.default_transformation_model or defaults.default_chat_model
            )
        elif model_type == "tools":
            model_id = defaults.default_tools_model or defaults.default_chat_model
        elif model_type == "embedding":
            model_id = defaults.default_embedding_model
        elif model_type == "text_to_speech":
            model_id = defaults.default_text_to_speech_model
        elif model_type == "speech_to_text":
            model_id = defaults.default_speech_to_text_model
        elif model_type == "large_context":
            model_id = defaults.large_context_model

        if not model_id:
            logger.warning(
                f"No default model configured for type '{model_type}'. "
                f"Please go to Settings → Models and set a default model."
            )
            return None

        try:
            return await self.get_model(model_id, **kwargs)
        except (ValueError, ConfigurationError) as e:
            logger.error(
                f"Failed to load default model for type '{model_type}': {e}. "
                f"The configured model_id '{model_id}' may have been deleted or misconfigured. "
                f"Please go to Settings → Models and reconfigure the default model."
            )
            return None


model_manager = ModelManager()
