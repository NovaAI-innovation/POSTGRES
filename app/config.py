from __future__ import annotations

import os
from dataclasses import dataclass


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _load_dotenv(path: str = ".env", override: bool = True) -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            current = os.environ.get(key, "")
            missing = key not in os.environ or not current.strip()
            if key and (override or missing):
                os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    database_url: str
    embedding_model: str
    auth_secret_current: str
    auth_secret_previous: str | None
    internal_api_keys: tuple[str, ...]
    log_level: str
    tool_timeout_seconds: int
    app_env: str
    codex_project_scope_group_id: str
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    @property
    def allow_dev_api_key(self) -> bool:
        return self.app_env != "production" and bool(self.internal_api_keys)

    @staticmethod
    def from_env() -> "Settings":
        # Precedence:
        # 1) explicit process environment
        # 2) .env
        # 3) .env.docker as fallback
        _load_dotenv(".env", override=False)
        if not (os.getenv("SUPABASE_URL", "").strip() and os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()):
            _load_dotenv(".env.docker", override=False)
        return Settings(
            database_url=os.getenv(
                "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agent_memory"
            ),
            supabase_url=os.getenv("SUPABASE_URL") or None,
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY") or None,
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            auth_secret_current=os.getenv("AUTH_SECRET_CURRENT", "dev-secret-change-me"),
            auth_secret_previous=os.getenv("AUTH_SECRET_PREVIOUS") or None,
            internal_api_keys=tuple(_split_csv(os.getenv("INTERNAL_API_KEYS", "dev-api-key"))),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            tool_timeout_seconds=int(os.getenv("TOOL_TIMEOUT_SECONDS", "30")),
            app_env=os.getenv("APP_ENV", "development"),
            codex_project_scope_group_id=os.getenv("CODEX_PROJECT_SCOPE_GROUP_ID", "project-codex"),
        )
