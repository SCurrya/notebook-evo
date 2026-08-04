from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from open_notebook.ai.model_assignment import auto_assign_default_models


@pytest.fixture
def client():
    """Create test client after environment variables have been cleared by conftest."""
    from api.main import app

    return TestClient(app)


class TestModelCreation:
    """Test suite for Model Creation endpoint."""

    @pytest.mark.asyncio
    @patch("open_notebook.database.repository.repo_query")
    @patch("api.routers.models.Model.save")
    async def test_create_duplicate_model_same_case(
        self, mock_save, mock_repo_query, client
    ):
        """Test that creating a duplicate model with same case returns 400."""
        # Mock repo_query to return a duplicate model
        mock_repo_query.return_value = [
            {
                "id": "model:123",
                "name": "gpt-4",
                "provider": "openai",
                "type": "language",
            }
        ]

        # Attempt to create duplicate
        response = client.post(
            "/api/models",
            json={"name": "gpt-4", "provider": "openai", "type": "language"},
        )

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Model 'gpt-4' already exists for provider 'openai' with type 'language'"
        )

    @pytest.mark.asyncio
    @patch("open_notebook.database.repository.repo_query")
    @patch("api.routers.models.Model.save")
    async def test_create_duplicate_model_different_case(
        self, mock_save, mock_repo_query, client
    ):
        """Test that creating a duplicate model with different case returns 400."""
        # Mock repo_query to return a duplicate model (case-insensitive match)
        mock_repo_query.return_value = [
            {
                "id": "model:123",
                "name": "gpt-4",
                "provider": "openai",
                "type": "language",
            }
        ]

        # Attempt to create duplicate with different case
        response = client.post(
            "/api/models",
            json={"name": "GPT-4", "provider": "OpenAI", "type": "language"},
        )

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Model 'GPT-4' already exists for provider 'OpenAI' with type 'language'"
        )

    @pytest.mark.asyncio
    @patch("open_notebook.database.repository.repo_query")
    async def test_create_same_model_name_different_provider(
        self, mock_repo_query, client
    ):
        """Test that creating a model with same name but different provider is allowed."""
        from open_notebook.ai.models import Model

        # Mock repo_query to return empty (no duplicate found for different provider)
        mock_repo_query.return_value = []

        # Patch the save method on the Model class
        with patch.object(Model, "save", new_callable=AsyncMock) as mock_save:
            # Attempt to create same model name with different provider (anthropic)
            response = client.post(
                "/api/models",
                json={"name": "gpt-4", "provider": "anthropic", "type": "language"},
            )

            # Should succeed because provider is different
            assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("open_notebook.database.repository.repo_query")
    async def test_create_same_model_name_different_type(self, mock_repo_query, client):
        """Test that creating a model with same name but different type is allowed."""
        from open_notebook.ai.models import Model

        # Mock repo_query to return empty (no duplicate found for different type)
        mock_repo_query.return_value = []

        # Patch the save method on the Model class
        with patch.object(Model, "save", new_callable=AsyncMock) as mock_save:
            # Attempt to create same model name with different type (embedding instead of language)
            response = client.post(
                "/api/models",
                json={"name": "gpt-4", "provider": "openai", "type": "embedding"},
            )

            # Should succeed because type is different
            assert response.status_code == 200


class TestModelsProviderAvailability:
    """Test suite for Models Provider Availability endpoint."""

    @patch("api.routers.models.os.environ.get")
    @patch("api.routers.models.AIFactory.get_available_providers")
    def test_generic_env_var_enables_all_modes(self, mock_esperanto, mock_env, client):
        """Test that OPENAI_COMPATIBLE_BASE_URL enables all 4 modes."""

        # Mock environment: only generic var is set
        def env_side_effect(key):
            if key == "OPENAI_COMPATIBLE_BASE_URL":
                return "http://localhost:1234/v1"
            return None

        mock_env.side_effect = env_side_effect

        # Mock Esperanto response
        mock_esperanto.return_value = {
            "language": ["openai-compatible"],
            "embedding": ["openai-compatible"],
            "speech_to_text": ["openai-compatible"],
            "text_to_speech": ["openai-compatible"],
        }

        response = client.get("/api/models/providers")

        assert response.status_code == 200
        data = response.json()

        # openai-compatible should be available
        assert "openai_compatible" in data["available"]

        # Should support all 4 types
        assert "openai_compatible" in data["supported_types"]
        supported = data["supported_types"]["openai_compatible"]
        assert "language" in supported
        assert "embedding" in supported
        assert "speech_to_text" in supported
        assert "text_to_speech" in supported
        assert len(supported) == 4

    @patch("api.routers.models.os.environ.get")
    @patch("api.routers.models.AIFactory.get_available_providers")
    def test_mode_specific_env_vars_llm_embedding(
        self, mock_esperanto, mock_env, client
    ):
        """Test mode-specific env vars (LLM + EMBEDDING) enable only those 2 modes."""

        # Mock environment: only LLM and EMBEDDING specific vars are set
        def env_side_effect(key):
            if key == "OPENAI_COMPATIBLE_BASE_URL_LLM":
                return "http://localhost:1234/v1"
            if key == "OPENAI_COMPATIBLE_BASE_URL_EMBEDDING":
                return "http://localhost:8080/v1"
            return None

        mock_env.side_effect = env_side_effect

        # Mock Esperanto response
        mock_esperanto.return_value = {
            "language": ["openai-compatible"],
            "embedding": ["openai-compatible"],
            "speech_to_text": ["openai-compatible"],
            "text_to_speech": ["openai-compatible"],
        }

        response = client.get("/api/models/providers")

        assert response.status_code == 200
        data = response.json()

        # openai-compatible should be available
        assert "openai_compatible" in data["available"]

        # Should support only language and embedding
        assert "openai_compatible" in data["supported_types"]
        supported = data["supported_types"]["openai_compatible"]
        assert "language" in supported
        assert "embedding" in supported
        assert "speech_to_text" not in supported
        assert "text_to_speech" not in supported
        assert len(supported) == 2

    @patch("api.routers.models.os.environ.get")
    @patch("api.routers.models.AIFactory.get_available_providers")
    def test_no_env_vars_set(self, mock_esperanto, mock_env, client):
        """Test that openai-compatible is not available when no env vars are set."""

        # Mock environment: no openai-compatible vars are set
        def env_side_effect(key):
            return None

        mock_env.side_effect = env_side_effect

        # Mock Esperanto response
        mock_esperanto.return_value = {
            "language": ["openai-compatible"],
            "embedding": ["openai-compatible"],
        }

        response = client.get("/api/models/providers")

        assert response.status_code == 200
        data = response.json()

        # openai-compatible should NOT be available
        assert "openai_compatible" not in data["available"]
        assert "openai_compatible" in data["unavailable"]

        # Should not have supported_types entry
        assert "openai_compatible" not in data["supported_types"]

    @patch("api.routers.models.os.environ.get")
    @patch("api.routers.models.AIFactory.get_available_providers")
    def test_mixed_config_generic_and_mode_specific(
        self, mock_esperanto, mock_env, client
    ):
        """Test mixed config: generic + mode-specific (generic should enable all)."""

        # Mock environment: both generic and mode-specific vars are set
        def env_side_effect(key):
            if key == "OPENAI_COMPATIBLE_BASE_URL":
                return "http://localhost:1234/v1"
            if key == "OPENAI_COMPATIBLE_BASE_URL_LLM":
                return "http://localhost:5678/v1"
            return None

        mock_env.side_effect = env_side_effect

        # Mock Esperanto response
        mock_esperanto.return_value = {
            "language": ["openai-compatible"],
            "embedding": ["openai-compatible"],
            "speech_to_text": ["openai-compatible"],
            "text_to_speech": ["openai-compatible"],
        }

        response = client.get("/api/models/providers")

        assert response.status_code == 200
        data = response.json()

        # openai-compatible should be available
        assert "openai_compatible" in data["available"]

        # Generic var enables all, so all 4 should be supported
        assert "openai_compatible" in data["supported_types"]
        supported = data["supported_types"]["openai_compatible"]
        assert "language" in supported
        assert "embedding" in supported
        assert "speech_to_text" in supported
        assert "text_to_speech" in supported
        assert len(supported) == 4

    @patch("api.routers.models.os.environ.get")
    @patch("api.routers.models.AIFactory.get_available_providers")
    def test_individual_mode_llm_only(self, mock_esperanto, mock_env, client):
        """Test individual mode-specific var (LLM only)."""

        # Mock environment: only LLM specific var is set
        def env_side_effect(key):
            if key == "OPENAI_COMPATIBLE_BASE_URL_LLM":
                return "http://localhost:1234/v1"
            return None

        mock_env.side_effect = env_side_effect

        # Mock Esperanto response
        mock_esperanto.return_value = {
            "language": ["openai-compatible"],
            "embedding": ["openai-compatible"],
            "speech_to_text": ["openai-compatible"],
            "text_to_speech": ["openai-compatible"],
        }

        response = client.get("/api/models/providers")

        assert response.status_code == 200
        data = response.json()

        # Should support only language
        supported = data["supported_types"]["openai_compatible"]
        assert supported == ["language"]

    @patch("api.routers.models.os.environ.get")
    @patch("api.routers.models.AIFactory.get_available_providers")
    def test_individual_mode_embedding_only(self, mock_esperanto, mock_env, client):
        """Test individual mode-specific var (EMBEDDING only)."""

        # Mock environment: only EMBEDDING specific var is set
        def env_side_effect(key):
            if key == "OPENAI_COMPATIBLE_BASE_URL_EMBEDDING":
                return "http://localhost:8080/v1"
            return None

        mock_env.side_effect = env_side_effect

        # Mock Esperanto response
        mock_esperanto.return_value = {
            "language": ["openai-compatible"],
            "embedding": ["openai-compatible"],
            "speech_to_text": ["openai-compatible"],
            "text_to_speech": ["openai-compatible"],
        }

        response = client.get("/api/models/providers")

        assert response.status_code == 200
        data = response.json()

        # Should support only embedding
        supported = data["supported_types"]["openai_compatible"]
        assert supported == ["embedding"]

    @patch("api.routers.models.os.environ.get")
    @patch("api.routers.models.AIFactory.get_available_providers")
    def test_individual_mode_stt_only(self, mock_esperanto, mock_env, client):
        """Test individual mode-specific var (STT only)."""

        # Mock environment: only STT specific var is set
        def env_side_effect(key):
            if key == "OPENAI_COMPATIBLE_BASE_URL_STT":
                return "http://localhost:9000/v1"
            return None

        mock_env.side_effect = env_side_effect

        # Mock Esperanto response
        mock_esperanto.return_value = {
            "language": ["openai-compatible"],
            "embedding": ["openai-compatible"],
            "speech_to_text": ["openai-compatible"],
            "text_to_speech": ["openai-compatible"],
        }

        response = client.get("/api/models/providers")

        assert response.status_code == 200
        data = response.json()

        # Should support only speech_to_text
        supported = data["supported_types"]["openai_compatible"]
        assert supported == ["speech_to_text"]

    @patch("api.routers.models.os.environ.get")
    @patch("api.routers.models.AIFactory.get_available_providers")
    def test_individual_mode_tts_only(self, mock_esperanto, mock_env, client):
        """Test individual mode-specific var (TTS only)."""

        # Mock environment: only TTS specific var is set
        def env_side_effect(key):
            if key == "OPENAI_COMPATIBLE_BASE_URL_TTS":
                return "http://localhost:9000/v1"
            return None

        mock_env.side_effect = env_side_effect

        # Mock Esperanto response
        mock_esperanto.return_value = {
            "language": ["openai-compatible"],
            "embedding": ["openai-compatible"],
            "speech_to_text": ["openai-compatible"],
            "text_to_speech": ["openai-compatible"],
        }

        response = client.get("/api/models/providers")

        assert response.status_code == 200
        data = response.json()

        # Should support only text_to_speech
        supported = data["supported_types"]["openai_compatible"]
        assert supported == ["text_to_speech"]


class TestModelSyncAndAssignment:
    """Test suite for model sync and auto-assignment flows."""

    @patch("api.routers.models.sync_all_providers", new_callable=AsyncMock)
    def test_sync_all_models_returns_aggregates(self, mock_sync_all, client):
        """Sync-all should aggregate provider counts into a single response."""

        mock_sync_all.return_value = {
            "openai": (3, 2, 1),
            "openrouter": (4, 1, 3),
        }

        response = client.post("/api/models/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["total_discovered"] == 7
        assert data["total_new"] == 3
        assert data["results"]["openai"]["discovered"] == 3
        assert data["results"]["openrouter"]["existing"] == 3

    @pytest.mark.asyncio
    @patch("open_notebook.ai.model_discovery.repo_query", new_callable=AsyncMock)
    async def test_sync_provider_reclassifies_same_name_model_type(
        self, mock_repo_query
    ):
        """Syncing a provider should correct a model type when the name already exists."""
        from open_notebook.ai.model_discovery import sync_provider_models

        mock_repo_query.return_value = [
            {
                "id": "model:openrouter-whisper",
                "name": "openai/whisper-1",
                "provider": "openrouter",
                "type": "text_to_speech",
            }
        ]

        with patch(
            "open_notebook.ai.model_discovery.discover_provider_models",
            new_callable=AsyncMock,
        ) as mock_discover:
            with patch("open_notebook.ai.model_discovery.Model", autospec=True) as mock_model_cls:
                mock_discover.return_value = [
                    type(
                        "DM",
                        (),
                        {
                            "name": "openai/whisper-1",
                            "provider": "openrouter",
                            "model_type": "speech_to_text",
                            "description": None,
                        },
                    )()
                ]
                mock_instance = AsyncMock()
                mock_instance.type = "text_to_speech"
                mock_instance.save = AsyncMock()
                mock_model_cls.return_value = mock_instance

                discovered, new, existing = await sync_provider_models(
                    "openrouter", auto_register=True
                )

        assert discovered == 1
        assert new == 0
        assert existing == 1
        assert mock_instance.save.await_count == 1

    @pytest.mark.asyncio
    @patch("open_notebook.ai.model_assignment.repo_query", new_callable=AsyncMock)
    @patch("open_notebook.ai.model_assignment.DefaultModels.get_instance", new_callable=AsyncMock)
    async def test_auto_assign_default_models_picks_preferred_models(
        self, mock_get_defaults, mock_repo_query
    ):
        """Auto assignment should pick preferred models and persist the defaults."""

        fake_defaults = AsyncMock()
        fake_defaults.default_chat_model = None
        fake_defaults.default_transformation_model = None
        fake_defaults.default_tools_model = None
        fake_defaults.large_context_model = None
        fake_defaults.default_embedding_model = None
        fake_defaults.default_text_to_speech_model = None
        fake_defaults.default_speech_to_text_model = None
        fake_defaults.update = AsyncMock()
        mock_get_defaults.return_value = fake_defaults

        mock_repo_query.return_value = [
            {
                "id": "model:openai-chat",
                "name": "gpt-4o",
                "provider": "openai",
                "type": "language",
            },
            {
                "id": "model:openai-embed",
                "name": "text-embedding-3-small",
                "provider": "openai",
                "type": "embedding",
            },
            {
                "id": "model:openai-tts",
                "name": "tts-1",
                "provider": "openai",
                "type": "text_to_speech",
            },
            {
                "id": "model:openai-stt",
                "name": "whisper-1",
                "provider": "openai",
                "type": "speech_to_text",
            },
        ]

        result = await auto_assign_default_models()

        assert result["assigned"]["default_chat_model"] == "model:openai-chat"
        assert result["assigned"]["default_embedding_model"] == "model:openai-embed"
        assert result["assigned"]["default_text_to_speech_model"] == "model:openai-tts"
        assert result["assigned"]["default_speech_to_text_model"] == "model:openai-stt"
        assert fake_defaults.default_chat_model == "model:openai-chat"
        assert fake_defaults.default_embedding_model == "model:openai-embed"
        fake_defaults.update.assert_awaited_once()
