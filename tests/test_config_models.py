from backend.core import config


class _FakeGeminiResponse:
    status_code = 200

    def json(self):
        return {
            "data": [
                {"id": "models/gemini-3.1-pro-preview"},
                {"id": "models/gemini-3.6-flash"},
                {"id": "models/gemini-2.5-flash"},
                {"id": "models/gemini-random-preview"},
                {"id": "models/gemini-embedding-test"},
            ]
        }


class _FakeDeepInfraResponse:
    status_code = 200

    def json(self):
        return {
            "data": [
                {"id": "anthropic/claude-sonnet-4-6"},
                {"id": "deepseek-ai/DeepSeek-V3.2"},
                {"id": "openai/gpt-test"},
            ]
        }


class _FakeUnauthorizedResponse:
    status_code = 401

    def json(self):
        return {"error": "invalid key"}


class _FakeGeminiClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def get(self, *args, **kwargs):
        return _FakeGeminiResponse()


class _FakeDeepInfraClient(_FakeGeminiClient):
    def get(self, *args, **kwargs):
        return _FakeDeepInfraResponse()


class _FakeUnauthorizedClient(_FakeGeminiClient):
    def get(self, *args, **kwargs):
        return _FakeUnauthorizedResponse()


def test_get_gemini_models_keeps_recommended_preview_models(monkeypatch):
    config.get_gemini_models.cache_clear()
    monkeypatch.setattr(config.httpx, "Client", _FakeGeminiClient)

    try:
        models = config.get_gemini_models("AIza-valid-test-key")

        assert "gemini-3.1-pro-preview" in models
        assert "gemini-3.6-flash" in models
        assert "gemini-2.5-flash" in models
        assert "gemini-random-preview" not in models
        assert "gemini-embedding-test" not in models
    finally:
        config.get_gemini_models.cache_clear()


def test_get_deepinfra_models_keeps_anthropic_claude_models(monkeypatch):
    config.get_deepinfra_models.cache_clear()
    monkeypatch.setattr(config.httpx, "Client", _FakeDeepInfraClient)

    try:
        models = config.get_deepinfra_models("di-valid-test-key")

        assert "anthropic/claude-sonnet-4-6" in models
        assert "deepseek-ai/DeepSeek-V3.2" in models
        assert "openai/gpt-test" not in models
    finally:
        config.get_deepinfra_models.cache_clear()


def test_get_models_return_empty_for_rejected_api_key(monkeypatch):
    config.get_openai_models.cache_clear()
    monkeypatch.setattr(config.httpx, "Client", _FakeUnauthorizedClient)

    try:
        assert config.get_openai_models("sk-invalid-test-key") == []
    finally:
        config.get_openai_models.cache_clear()


def test_is_deepinfra_model_routes_anthropic_claude_ids():
    assert config.is_deepinfra_model("anthropic/claude-sonnet-4-6")
