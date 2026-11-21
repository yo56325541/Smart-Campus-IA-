from typing import Protocol


class ConversationMemory(Protocol):
    """Contrat a implementer par SA-26 (stockage) et SA-37 (usage par le LLM)."""

    def get_history(self, conversation_id: str, limit: int) -> list[dict]: ...
    def append(self, conversation_id: str, role: str, content: str) -> None: ...


class InMemoryConversationMemory:
    """Implementation par defaut (dev/tests). Remplacee par la version BD."""

    def __init__(self) -> None:
        self._store: dict[str, list[dict]] = {}

    def get_history(self, conversation_id: str, limit: int) -> list[dict]:
        return self._store.get(conversation_id, [])[-limit:]

    def append(self, conversation_id: str, role: str, content: str) -> None:
        self._store.setdefault(conversation_id, []).append(
            {"role": role, "content": content}
        )
