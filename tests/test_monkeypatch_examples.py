import os


def test_monkeypatch_env(monkeypatch):
    # Temporarily set an env var; pytest restores the original after the test.
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    assert os.environ["OPENAI_API_KEY"] == "fake-key-for-test"


def test_monkeypatch_attr(monkeypatch):
    class Dummy:
        value = 1

    # Swap an attribute for the duration of the test.
    monkeypatch.setattr(Dummy, "value", 42)
    assert Dummy.value == 42
