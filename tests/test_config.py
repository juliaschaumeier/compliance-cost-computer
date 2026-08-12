from backend.core.config import Settings


def test_settings_default_model_is_unselected_when_not_configured(monkeypatch):
    monkeypatch.delenv("DEFAULT_MODEL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.default_model == ""


def test_settings_accept_shared_deployment_env_keys(tmp_path, monkeypatch):
    for key in (
        "AUTH_SECRET_KEY",
        "ADMIN_BOOTSTRAP_EMAIL",
        "ADMIN_BOOTSTRAP_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "DOMAIN=http://localhost",
                "NEXT_PUBLIC_API_BASE_URL=/api",
                "AUTH_SECRET_KEY=test-secret",
                "ADMIN_BOOTSTRAP_EMAIL=admin@example.com",
                "ADMIN_BOOTSTRAP_PASSWORD=choose-a-password",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.auth_secret_key == "test-secret"
    assert settings.admin_bootstrap_email == "admin@example.com"
