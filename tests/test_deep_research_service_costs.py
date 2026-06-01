from types import SimpleNamespace

from backend.core import deep_research_service


class _FakeInteractions:
    callback_seen_before_get = False

    def create(self, **_kwargs):
        return SimpleNamespace(id="interaction-1")

    def get(self, id):
        assert id == "interaction-1"
        assert self.callback_seen_before_get is True
        return SimpleNamespace(
            id=id,
            status="completed",
            outputs=[SimpleNamespace(text="Research report")],
            usage={
                "total_input_tokens": "1000000",
                "total_output_tokens": 2_000_000,
                "total_thought_tokens": 500_000,
                "total_tokens": 3_500_000,
            },
        )


class _FakeClient:
    def __init__(self, **_kwargs):
        self.interactions = _FakeInteractions()


def test_deep_research_result_includes_estimated_cost(monkeypatch):
    monkeypatch.setattr(deep_research_service.genai, "Client", _FakeClient)
    _FakeInteractions.callback_seen_before_get = False
    started = []

    def record_start(agent, interaction_id):
        started.append((agent, interaction_id))
        _FakeInteractions.callback_seen_before_get = True

    result = deep_research_service._run_interaction_sync(
        api_key="test-key",
        prompt="prompt",
        agent="deep-research-preview-04-2026",
        poll_interval_seconds=1,
        on_interaction_started=record_start,
    )

    assert started == [("deep-research-preview-04-2026", "interaction-1")]
    assert result.input_tokens == 1_000_000
    assert result.output_tokens == 2_000_000
    assert result.thought_tokens == 500_000
    assert result.total_tokens == 3_500_000
    assert result.estimated_cost_usd == 32.0
