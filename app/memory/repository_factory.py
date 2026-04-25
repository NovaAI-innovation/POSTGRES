from __future__ import annotations

import logging

from app.config import Settings
from app.memory.repository import InMemoryMemoryRepository, MemoryRepository
from app.memory.postgres_repository import PostgresMemoryRepository
from app.memory.supabase_repository import SupabaseMemoryRepository


def build_memory_repository(settings: Settings) -> MemoryRepository:
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabaseMemoryRepository(settings.supabase_url, settings.supabase_service_role_key)
    if settings.app_env == "production":
        raise RuntimeError("supabase configuration is required in production")
    postgres = PostgresMemoryRepository(settings.database_url)
    if postgres.is_available():
        return postgres
    logging.getLogger(__name__).warning("postgres_unavailable_falling_back_to_inmemory")
    return InMemoryMemoryRepository()
