from __future__ import annotations

from app.config import Settings


def test_from_env_uses_env_docker_as_supabase_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    (tmp_path / ".env").write_text("APP_ENV=development\n", encoding="utf-8")
    (tmp_path / ".env.docker").write_text(
        "SUPABASE_URL=https://example.supabase.co\nSUPABASE_SERVICE_ROLE_KEY=service-role\n",
        encoding="utf-8",
    )

    settings = Settings.from_env()
    assert settings.supabase_url == "https://example.supabase.co"
    assert settings.supabase_service_role_key == "service-role"


def test_from_env_does_not_override_existing_process_env(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUPABASE_URL", "https://runtime.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "runtime-key")

    (tmp_path / ".env").write_text(
        "SUPABASE_URL=https://file.supabase.co\nSUPABASE_SERVICE_ROLE_KEY=file-key\n",
        encoding="utf-8",
    )

    settings = Settings.from_env()
    assert settings.supabase_url == "https://runtime.supabase.co"
    assert settings.supabase_service_role_key == "runtime-key"
