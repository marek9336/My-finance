import hashlib
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass
class SyncStats:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    canceled: int = 0
    failed: int = 0


def compute_event_uid(source: str, source_entity_id: UUID, due_at_iso: str) -> str:
    return f"{source}:{source_entity_id}:{due_at_iso[:10]}"


def compute_event_hash(title: str, message: str | None, due_at_iso: str, timezone: str) -> str:
    payload = f"{title}|{message or ''}|{due_at_iso}|{timezone}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_provider_event_id() -> str:
    return f"evt_{uuid4()}"
