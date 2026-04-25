from __future__ import annotations

from app.config import Settings
from app.memory import repository_factory
from app.memory.postgres_repository import PostgresMemoryRepository
from app.memory.repository import InMemoryMemoryRepository
from app.memory.supabase_repository import SupabaseMemoryRepository


def _settings(*, supabase: bool = False) -> Settings:
    return Settings(
        database_url="postgresql://postgres:postgres@localhost:5432/agent_memory",
        embedding_model="all-MiniLM-L6-v2",
        auth_secret_current="test-secret",
        auth_secret_previous=None,
        internal_api_keys=("dev-api-key",),
        log_level="INFO",
        tool_timeout_seconds=30,
        app_env="development",
        codex_project_scope_group_id="project-codex",
        supabase_url="https://example.supabase.co" if supabase else None,
        supabase_service_role_key="service-role" if supabase else None,
    )


def test_factory_prefers_supabase_when_credentials_provided() -> None:
    repo = repository_factory.build_memory_repository(_settings(supabase=True))
    assert isinstance(repo, SupabaseMemoryRepository)


def test_factory_uses_postgres_when_available(monkeypatch) -> None:
    monkeypatch.setattr(PostgresMemoryRepository, "is_available", lambda self: True)
    repo = repository_factory.build_memory_repository(_settings())
    assert isinstance(repo, PostgresMemoryRepository)


def test_factory_falls_back_to_inmemory_when_postgres_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(PostgresMemoryRepository, "is_available", lambda self: False)
    repo = repository_factory.build_memory_repository(_settings())
    assert isinstance(repo, InMemoryMemoryRepository)
