from __future__ import annotations

from app.config import Settings
from app.memory.repository import InMemoryMemoryRepository, MemoryRepository
from app.memory.supabase_repository import SupabaseMemoryRepository


def build_memory_repository(settings: Settings) -> MemoryRepository:
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabaseMemoryRepository(settings.supabase_url, settings.supabase_service_role_key)
    return InMemoryMemoryRepository()
